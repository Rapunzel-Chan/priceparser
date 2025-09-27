import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from decimal import Decimal

from price_parser.models import (
    Product,
    ParsedProduct,
    ProductPriceHistory,
    ParserSchedule,
    ParsedProductArchive
)
from price_parser.services.lemana_parse import LemanaProScraper
from price_parser.services.lemana_service import lemana_parse_saved
from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack




import logging
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from price_parser.models import Product, ParsedProduct
from .services.lemana_service import lemana_parse_saved

import logging
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from price_parser.models import Product, ParsedProduct
from .services.lemana_service import lemana_parse_saved
import os

logger = logging.getLogger(__name__)
PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)


def notify_user_parsing_done(user, products):
    product_names = ", ".join([p.name for p in products])
    reports_url = f"{settings.SITE_URL.rstrip('/')}/reports/"
    send_mail(
        subject="Парсинг завершён",
        message=f"Ваш парсинг завершён.\nТовары: {product_names}\nПосмотреть результаты: {reports_url}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
    )


@shared_task(bind=True)
def parse_products_batch_task(self, product_ids, user_id=None):
    logger.info(f"🔹 Запуск парсинга продуктов: {product_ids}")
    total_parsed = 0

    for pid in product_ids:
        try:
            product = Product.objects.get(pk=pid)
        except Product.DoesNotExist:
            logger.warning(f"❌ Продукт с id={pid} не найден")
            continue

        try:
            # Используем новый стабильный парсер
            avg_price = lemana_parse_saved(product.name, product_id=pid, owner=product.owner)
            if avg_price:
                total_parsed += 1
                logger.info(f"💰 {product.name} — средняя цена: {avg_price}")
            else:
                logger.warning(f"⚠️ Не удалось спарсить {product.name}. Скриншот сохранён в {PARSED_DIR}")

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга {product.name}: {e}")
            # Попытка сохранить скриншот, если есть доступ к driver
            try:
                from services.lemana_parse import LemanaProScraper
                screenshot_path = os.path.join(PARSED_DIR, f"error_task_{product.name}.png")
                # Заглушка: здесь driver уже закрыт, но если нужен отдельный дебаг:
                logger.info(f"💾 Попробуйте проверить {screenshot_path}")
            except Exception:
                pass

        # Отмечаем продукт как обработанный
        product.parsing_done = True
        product.save()

    logger.info(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")

    # Отправка уведомления пользователю
    if user_id:
        try:
            user = get_user_model().objects.get(pk=user_id)
            products = Product.objects.filter(id__in=product_ids)
            notify_user_parsing_done(user, products)
        except Exception:
            logger.exception("Ошибка при уведомлении пользователя")


@shared_task
def parse_parser_products(parser_id: int):
    from .models import ParserSchedule
    parser = ParserSchedule.objects.get(pk=parser_id)
    product_ids = list(parser.products.values_list('id', flat=True))
    parse_products_batch_task.delay(product_ids, user_id=parser.owner.id)
    parser.last_run = timezone.now()
    parser.save()



# @shared_task
# def recalculate_product_prices(product_ids=None):
#     """
#     Пересчитывает средние цены для продуктов и обновляет историю
#     """
#     if product_ids is None:
#         products = Product.objects.all()
#     else:
#         products = Product.objects.filter(id__in=product_ids)
#
#     today = timezone.now().date()
#     updated_count = 0
#
#     for product in products:
#         try:
#             # Получаем все связанные записи парсинга
#             parsed_products = ParsedProduct.objects.filter(product=product)
#
#             if not parsed_products.exists():
#                 continue
#
#             # Рассчитываем среднюю цену за единицу
#             unit_prices = []
#             for pp in parsed_products:
#                 if pp.price is None:
#                     continue
#                 pack_size = pp.pack_size or Decimal(1)
#                 unit_prices.append(pp.price / pack_size)
#
#             avg_price = filtered_unique_mean(unit_prices)
#
#             if avg_price is not None:
#                 # Обновляем среднюю цену продукта
#                 product.avg_price_lemanapro = avg_price
#                 product.parsed = True
#                 product.save()
#
#                 # Обновляем историю цен
#                 ProductPriceHistory.objects.update_or_create(
#                     product=product,
#                     date=today,
#                     defaults={'avg_price_per_unit': avg_price}
#                 )
#
#                 updated_count += 1
#                 logger.info(f"✅ Обновлена цена для {product.name}: {avg_price}")
#         except Exception as e:
#             logger.error(f"❌ Ошибка при пересчете цены для {product.name}: {str(e)}")
#
#     logger.info(f"✅ Пересчет цен завершен. Обновлено продуктов: {updated_count}")
#     return updated_count
#
#
# def notify_user_parsing_done(user, products):
#     """
#     Отправляет уведомление пользователю о завершении парсинга
#     """
#     product_names = ", ".join([p.name for p in products])
#     reports_url = f"{settings.SITE_URL.rstrip('/')}{reverse('price_parser:reports')}"
#
#     send_mail(
#         subject="Парсинг завершён",
#         message=f"Ваш парсинг завершён.\nТовары: {product_names}\nПосмотреть результаты: {reports_url}",
#         from_email=settings.EMAIL_HOST_USER,
#         recipient_list=[user.email],
#         fail_silently=False,
#     )
#
# @shared_task
# def parse_parser_products(parser_id: int):
#     from .models import ParserSchedule
#     parser = ParserSchedule.objects.get(pk=parser_id)
#     product_ids = list(parser.products.values_list('id', flat=True))
#     parse_products_batch_task.delay(product_ids, user_id=parser.owner.id)
#     parser.last_run = timezone.now()
#     parser.save()

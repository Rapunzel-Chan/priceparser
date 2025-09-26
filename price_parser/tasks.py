from celery import shared_task
from django.utils import timezone
from price_parser.models import Product, ParsedProduct
from .services.lemana_parse import LemanaProScraper
import logging

logger = logging.getLogger(__name__)
import logging
from celery import shared_task
from price_parser.services.lemana_service import lemana_parse_saved
from price_parser.models import Product
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model

from celery import shared_task
from django.utils import timezone
from price_parser.models import Product, ParsedProduct
from .services.lemana_parse import LemanaProScraper
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

# logger = logging.getLogger(__name__)

from celery import shared_task
from django.utils import timezone
from price_parser.models import Product, ParsedProduct
from .services.lemana_parse import LemanaProScraper
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from price_parser.utils.price_utils import filtered_unique_mean
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def parse_products_batch_task(self, product_ids, user_id=None):
    """
    product_ids: list of product ids (int)
    """
    logger.info(f"🔹 Запуск парсинга продуктов: {product_ids}")
    scraper = LemanaProScraper(headless=True)
    total_parsed = 0

    try:
        for pid in product_ids:
            try:
                product = Product.objects.get(id=int(pid))
            except Product.DoesNotExist:
                logger.warning(f"❌ Продукт с id={pid} не найден")
                continue

            try:
                result = scraper.find_matching_products(product.name)
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга {product.name}: {e}")
                continue

            if result and result.get("products"):
                for p in result["products"]:
                    # сохраняем pack_size и unit, если есть
                    pack_size = p.get("pack_size") or Decimal(1)
                    unit = p.get("unit") or None
                    ParsedProduct.objects.create(
                        name=p["name"],
                        price=p["price"],
                        unit=unit,
                        pack_size=pack_size,
                        url=p.get("url"),
                        source="lemanapro",
                        product=product,
                        owner=product.owner
                    )
                    total_parsed += 1

            # после обработки данного продукта пересчитываем среднюю цену за единицу
            all_pp = product.parsed_products.all()
            unit_prices = []
            for pp in all_pp:
                if pp.price is None:
                    continue
                ps = pp.pack_size or Decimal(1)
                unit_prices.append((pp.price / ps) if ps else pp.price)
            avg_price_per_unit = filtered_unique_mean(unit_prices)
            if avg_price_per_unit:
                product.avg_price_lemanapro = avg_price_per_unit
                product.parsed = True
                product.save()

            product.parsing_done = True
            product.save()

    finally:
        scraper.close()
        logger.info(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")

        if user_id:
            try:
                user = get_user_model().objects.get(pk=user_id)
                products = Product.objects.filter(id__in=product_ids)
                notify_user_parsing_done(user, products)
            except Exception:
                logger.exception("Ошибка при уведомлении пользователя")


from django.urls import reverse
from urllib.parse import urlencode


from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

def notify_user_parsing_done(user, products):
    product_names = ", ".join([p.name for p in products])
    reports_url = f"{settings.SITE_URL.rstrip('/')}{reverse('price_parser:reports')}"
    send_mail(
        subject="Парсинг завершён",
        message=f"Ваш парсинг завершён.\nТовары: {product_names}\nПосмотреть результаты: {reports_url}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
    )

@shared_task
def parse_parser_products(parser_id: int):
    from .models import ParserSchedule
    parser = ParserSchedule.objects.get(pk=parser_id)
    product_ids = list(parser.products.values_list('id', flat=True))
    parse_products_batch_task.delay(product_ids, user_id=parser.owner.id)
    parser.last_run = timezone.now()
    parser.save()

# @shared_task(bind=True)
# def parse_products_batch_task(self, product_ids, user_id=None):
#     logger.info(f"🔹 Запуск парсинга продуктов: {product_ids}")
#     scraper = LemanaProScraper(headless=False)
#     total_parsed = 0
#
#     try:
#         for pid in product_ids:
#             try:
#                 product = Product.objects.get(id=pid)
#             except Product.DoesNotExist:
#                 logger.warning(f"❌ Продукт с id={pid} не найден")
#                 continue
#
#             try:
#                 result = scraper.find_matching_products(product.name)
#             except Exception as e:
#                 logger.error(f"❌ Ошибка парсинга {product.name}: {e}")
#                 continue
#
#             if result and result.get("products"):
#                 for p in result["products"]:
#                     ParsedProduct.objects.create(
#                         name=p["name"],
#                         price=p["price"],
#                         unit=p.get("unit"),
#                         url=p.get("url"),
#                         source="lemanapro",
#                         product=product,
#                         owner=product.owner
#                     )
#                     total_parsed += 1
#
#             product.parsing_done = True
#             product.save()
#
#     finally:
#         scraper.close()
#         logger.info(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")
#
#         if user_id:
#             user = get_user_model().objects.get(pk=user_id)
#             products = Product.objects.filter(id__in=product_ids)
#             notify_user_parsing_done(user, products)
#
#
# def notify_user_parsing_done(user, products):
#     product_names = ", ".join([p.name for p in products])
#     send_mail(
#         subject="Парсинг завершён",
#         message=f"Ваш парсинг завершён.\nТовары: {product_names}\nПосмотреть результаты: http://example.com/reports/",
#         from_email=settings.EMAIL_HOST_USER,
#         recipient_list=[user.email],
#     )
#
#
# @shared_task
# def parse_parser_products(parser_id: int):
#     from .models import ParserSchedule
#     parser = ParserSchedule.objects.get(pk=parser_id)
#     product_ids = list(parser.products.values_list('id', flat=True))
#     parse_products_batch_task.delay(product_ids, user_id=parser.owner.id)
#     parser.last_run = timezone.now()
#     parser.save()

# @shared_task(bind=True)
# def parse_products_batch_task(self, product_ids):
#     """
#     Парсинг нескольких продуктов по ID через lemana_parse_saved.
#     Логирование каждого шага для контроля.
#     """
#     logger.info(f"🔹 Запуск парсинга продуктов: {product_ids}")
#     print(f"🔹 Запуск парсинга продуктов: {product_ids}")
#
#     total_parsed = 0
#
#     for pid in product_ids:
#         prod = Product.objects.filter(id=pid).first()
#         if not prod:
#             logger.warning(f"❌ Продукт с id={pid} не найден")
#             print(f"❌ Продукт с id={pid} не найден")
#             continue
#
#         logger.info(f"🔎 Парсер обрабатывает продукт: {prod.name}")
#         print(f"🔎 Парсер обрабатывает продукт: {prod.name}")
#
#         try:
#             avg_price = lemana_parse_saved(prod.name)
#             if avg_price is not None:
#                 logger.info(f"💰 Пропарсено: {prod.name} — средняя цена: {avg_price}")
#                 print(f"💰 Пропарсено: {prod.name} — средняя цена: {avg_price}")
#                 total_parsed += 1
#             else:
#                 logger.info(f"⚠️ Продукт {prod.name} не найден на сайте или нет цен")
#                 print(f"⚠️ Продукт {prod.name} не найден на сайте или нет цен")
#         except Exception as e:
#             logger.error(f"❌ Ошибка парсинга {prod.name}: {e}")
#             print(f"❌ Ошибка парсинга {prod.name}: {e}")
#             continue
#
#     logger.info(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")
#     print(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")
#
#     return f"Парсинг завершён для {total_parsed} товаров"

#
# @shared_task(bind=True)
# def parse_products_batch_task(self, product_ids):
#     """
#     Парсим список продуктов через LemanaProScraper.
#     Используется headless Chrome на Windows + Celery --pool=solo.
#     Логирование с подробностями по каждому продукту.
#     """
#     logger.info(f"🔹 Запуск парсинга продуктов: {product_ids}")
#     print(f"🔹 Запуск парсинга продуктов: {product_ids}")
#
#     scraper = LemanaProScraper(headless=False)
#     total_parsed = 0
#
#     try:
#         for pid in product_ids:
#             try:
#                 product = Product.objects.get(id=pid)
#             except Product.DoesNotExist:
#                 logger.warning(f"❌ Продукт с id={pid} не найден")
#                 print(f"❌ Продукт с id={pid} не найден")
#                 continue
#
#             logger.info(f"🔎 Парсер обрабатывает продукт: {product.name}")
#             print(f"🔎 Парсер обрабатывает продукт: {product.name}")
#
#             try:
#                 result = scraper.find_matching_products(product.name)
#             except Exception as e:
#                 logger.error(f"❌ Ошибка парсинга {product.name}: {e}")
#                 print(f"❌ Ошибка парсинга {product.name}: {e}")
#                 continue
#
#             if result and result.get("products"):
#                 for p in result["products"]:
#                     parsed_product = ParsedProduct.objects.create(
#                         name=p["name"],
#                         price=p["price"],
#                         unit=p.get("unit"),
#                         url=p.get("url"),
#                         source="lemanapro",
#                         product=product
#                     )
#                     logger.info(f"💰 Пропарсено: {parsed_product.name} — {parsed_product.price} {parsed_product.unit}")
#                     print(f"💰 Пропарсено: {parsed_product.name} — {parsed_product.price} {parsed_product.unit}")
#                     total_parsed += 1
#             else:
#                 logger.info(f"⚠️ Продукт {product.name} не найден на сайте")
#                 print(f"⚠️ Продукт {product.name} не найден на сайте")
#
#             # Отмечаем продукт как спарсенный (опционально)
#             product.parsing_done = True
#             product.save()
#
#     finally:
#         scraper.close()
#         logger.info(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")
#         print(f"✅ Все продукты обработаны. Всего спарсено: {total_parsed}")
#
#         if user_id:
#             from .models import Product
#             user = get_user_model().objects.get(pk=user_id)
#             products = Product.objects.filter(id__in=product_ids)
#             notify_user_parsing_done(user, products)
#
#
#
# def notify_user_parsing_done(user, products):
#     product_names = ", ".join([p.name for p in products])
#     send_mail(
#         subject="Парсинг завершён",
#         message=f"Ваш парсинг завершён.\nТовары: {product_names}\nПосмотреть результаты: http://example.com/reports/",
#         from_email=settings.EMAIL_HOST_USER,
#         recipient_list=[user.email],
#     )
#
# @shared_task
# def parse_parser_products(parser_id: int):
#     """
#     Парсинг всех товаров, связанных с конкретным ParserSchedule.
#     """
#     from .models import ParserSchedule
#     parser = ParserSchedule.objects.get(pk=parser_id)
#     product_ids = list(parser.products.values_list('id', flat=True))
#     parse_products_batch_task(product_ids, user_id=parser.owner.id)
#     parser.last_run = timezone.now()
#     parser.save()

# @shared_task
# def parse_products_batch_task(product_ids: list[int]):
#     """
#     Парсит список товаров по логике LemanaProScraper.
#     """
#     products = Product.objects.filter(id__in=product_ids)
#     scraper = LemanaProScraper(headless=True)
#
#     try:
#         for product in products:
#             result = scraper.find_matching_products(product.name)
#             if not result:
#                 continue
#
#             product.avg_price_lemanapro = result["avg_price"]
#             product.parsed = True
#             product.save()
#
#             for p in result["products"]:
#                 ParsedProduct.objects.create(
#                     product=product,
#                     name=p["name"],
#                     price=p["price"],
#                     unit=p["unit"],
#                     url=p["url"],
#                     source="lemanapro",
#                 )
#
#             filename = os.path.join("parsed_products", f"{product.name}.txt")
#             with open(filename, "w", encoding="utf-8") as f:
#                 for p in result["products"]:
#                     f.write(f"{p}\n")
#     finally:
#         scraper.close()


# @shared_task(bind=True)
# def parse_product_task(self, product_id):
#     try:
#         product = Product.objects.get(id=product_id)
#     except Product.DoesNotExist:
#         return {"error": "not_found"}
#
#     scraper = LemanaProScraper(headless=True)
#     try:
#         res = scraper.find_matching_products(product.name)
#         if not res:
#             return {"error": "no_results"}
#
#         products = res["products"]
#         avg_price = res["avg_price"]
#
#         # сохраняем отдельные ParsedProduct строки (топ N)
#         parsed_objs = []
#         for p in products:
#             parsed = ParsedProduct.objects.create(
#                 product=product,
#                 name=p["name"],
#                 price=p["price"],
#                 unit=p.get("unit"),
#                 url=p.get("url"),
#                 source="lemanapro"
#             )
#             parsed_objs.append(parsed)
#
#         # update product aggregated fields
#         product.avg_price_lemanapro = avg_price
#         # try to detect unit/pack
#         unit, pack = extract_unit_and_pack(product.name)
#         if unit:
#             product.unit = unit
#         if pack:
#             product.pack_size = pack
#         product.parsed = True
#         product.save()
#
#         return {
#             "avg_price": float(avg_price) if avg_price else None,
#             "parsed_count": len(parsed_objs)
#         }
#     finally:
#         scraper.close()
#
#
# @app.task
# def parse_parser_products(parser_id):
#     from price_parser.models import Parser, ParsedProduct
#     from price_parser.services.lemana_parse import LemanaProScraper
#
#     parser = Parser.objects.get(pk=parser_id)
#     scraper = LemanaProScraper(headless=True)
#     for product in parser.products.all():
#         data = scraper.find_matching_products(product.name)
#         if data:
#             ParsedProduct.objects.create(
#                 product=product,
#                 name=product.name,
#                 avg_price=data['avg_price'],
#                 url=data['products'][0]['url']
#             )
#             # отправляем письмо
#             send_mail(
#                 f"Обновление цены для {product.name}",
#                 f"Новая средняя цена: {data['avg_price']}",
#                 settings.DEFAULT_FROM_EMAIL,
#                 [parser.user.email],
#                 fail_silently=True
#             )
#     scraper.close()

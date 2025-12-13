import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from price_parser.models import ParsedProduct, ParserSchedule, Product, ProductPriceHistory
from price_parser.services.lemana_service import lemana_parse_saved
from price_parser.utils.price_utils import filtered_unique_mean

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def parse_products_batch_task(self, product_ids, user_id=None, parser_id=None):
    """
    Запускает парсинг для списка продуктов и обновляет цены
    """
    logger.info(f"Запуск парсинга продуктов: {product_ids}")
    total_parsed = 0

    for pid in product_ids:
        try:
            product = Product.objects.get(pk=pid)
        except Product.DoesNotExist:
            logger.warning(f"Продукт с id={pid} не найден")
            continue

        try:
            avg_price = lemana_parse_saved(
                product_name=product.name, product_id=pid, owner=product.owner, parser_id=parser_id
            )
            if avg_price:
                total_parsed += 1
                logger.info(f"{product.name} — средняя цена: {avg_price}")
        except Exception as e:
            logger.error(f" Ошибка парсинга {product.name}: {e}")

        product.parsing_done = True
        product.save()

    recalculate_product_prices(product_ids)

    logger.info(f"Все продукты обработаны. Всего спарсено: {total_parsed}")

    if user_id:
        try:
            user = get_user_model().objects.get(pk=user_id)
            products = Product.objects.filter(id__in=product_ids)
            notify_user_parsing_done(user, products, parser_id=parser_id)
        except Exception:
            logger.exception("Ошибка при уведомлении пользователя")


@shared_task
def parse_parser_products(parser_id: int):
    """
    Запускает парсинг для всех продуктов, связанных с парсером
    """
    try:
        parser = ParserSchedule.objects.get(pk=parser_id)
        product_ids = list(parser.products.values_list("id", flat=True))

        if not product_ids:
            logger.warning(f"Парсер {parser.name} не имеет связанных продуктов")
            return

        parse_products_batch_task.delay(product_ids, user_id=parser.owner.id, parser_id=parser.id)

        parser.last_run = timezone.now()
        parser.save()

        logger.info(f"Запущен парсинг для парсера {parser.name}")
    except ParserSchedule.DoesNotExist:
        logger.error(f"Парсер с id={parser_id} не найден")
    except Exception as e:
        logger.error(f"Ошибка при запуске парсера: {str(e)}")


@shared_task
def recalculate_product_prices(product_ids=None):
    """
    Пересчитывает средние цены для продуктов и обновляет историю
    """
    if product_ids is None:
        products = Product.objects.all()
    else:
        products = Product.objects.filter(id__in=product_ids)

    today = timezone.now().date()
    updated_count = 0

    for product in products:
        try:
            parsed_products = ParsedProduct.objects.filter(product=product)

            if not parsed_products.exists():
                continue

            unit_prices = []
            for pp in parsed_products:
                if pp.price is None:
                    continue

                if pp.price > Decimal("100000"):
                    logger.warning(f"Пропущена аномально высокая цена для {product.name}: {pp.price}")
                    continue

                pack_size = pp.pack_size or 1
                price_per_unit = pp.price / pack_size
                unit_prices.append(price_per_unit)

            avg_price = filtered_unique_mean(unit_prices) if unit_prices else None

            if avg_price is not None:
                product.avg_price_lemanapro = avg_price
                product.parsed = True
                product.save()

                ProductPriceHistory.objects.update_or_create(
                    product=product, date=today, defaults={"avg_price_per_unit": avg_price}
                )

                updated_count += 1
                logger.info(f"Обновлена цена для {product.name}: {avg_price}")
        except Exception as e:
            logger.error(f"Ошибка при пересчете цены для {product.name}: {str(e)}")

    logger.info(f"Пересчет цен завершен. Обновлено продуктов: {updated_count}")
    return updated_count


def notify_user_parsing_done(user, products, parser_id=None):
    """
    Отправляет уведомление пользователю о завершении парсинга
    """
    product_names = ", ".join([p.name for p in products])

    results_link = ""
    link_text = ""

    if parser_id:
        results_url = reverse("price_parser:parser_results", kwargs={"pk": parser_id})
        results_link = f"{settings.SITE_URL.rstrip('/')}{results_url}"
        link_text = "Посмотреть результаты парсера"
    else:
        reports_url = reverse("price_parser:reports")
        results_link = f"{settings.SITE_URL.rstrip('/')}{reports_url}"
        link_text = "Посмотреть отчеты"

    message = f"""
Здравствуйте, {user.username}!

Ваш парсинг завершен.

Товары: {product_names}
Всего обработано: {len(products)}

{link_text}: {results_link}

С уважением,
Команда вашего сервиса
    """

    send_mail(
        subject="Парсинг завершён",
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False,
    )

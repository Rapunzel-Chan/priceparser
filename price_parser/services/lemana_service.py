import os
from decimal import Decimal

from django.utils import timezone
from selenium.common.exceptions import WebDriverException

from price_parser.models import ParsedProduct, ParsedProductArchive, Product, ProductPriceHistory
from price_parser.utils.price_utils import extract_unit_and_pack, filtered_unique_mean

from .lemana_parse import LemanaProScraper

PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)


def update_product_price(prod_obj):
    """Обновляет среднюю цену продукта и историю цен."""
    if not prod_obj:
        return

    try:
        today = timezone.now().date()
        all_pp = ParsedProduct.objects.filter(product=prod_obj, fetched_at__date=today)
        unit_prices = []

        print(f"Для продукта '{prod_obj.name}' найдено {all_pp.count()} записей за сегодня")

        for pp in all_pp:
            if pp.price is None:
                continue

            if pp.price > Decimal("100000"):
                print(f"Пропущена аномально высокая цена для {prod_obj.name}: {pp.price}")
                continue

            pack_size = pp.pack_size or Decimal(1)
            if pack_size == 0:
                pack_size = Decimal(1)

            price_per_unit = pp.price / pack_size

            if price_per_unit > Decimal("1000"):
                print(f"Пропущена аномально высокая цена за единицу для {prod_obj.name}: {price_per_unit}")
                continue

            unit_prices.append(price_per_unit)
            print(f"Добавлена цена за единицу: {price_per_unit}")

        print(f"Все цены за единицу для расчета: {unit_prices}")

        avg_price_per_unit = filtered_unique_mean(unit_prices) if unit_prices else None

        prod_obj.avg_price_lemanapro = avg_price_per_unit
        prod_obj.parsed = bool(all_pp.exists())
        prod_obj.save()

        if avg_price_per_unit is not None:
            ProductPriceHistory.objects.update_or_create(
                product=prod_obj, date=today, defaults={"avg_price_per_unit": avg_price_per_unit}
            )
            print(f"Обновлена средняя цена для {prod_obj.name}: {avg_price_per_unit}")
        else:
            last_history = prod_obj.price_history.order_by("-date").first()
            if last_history:
                prod_obj.avg_price_lemanapro = last_history.avg_price_per_unit
                prod_obj.save()
                print(f"Восстановлена цена из истории для {prod_obj.name}: {last_history.avg_price_per_unit}")
    except Exception as e:
        print(f"Ошибка при обновлении цены для {prod_obj.name}: {e}")
        import traceback

        traceback.print_exc()


def lemana_parse_saved(product_name: str, product_id: int = None, owner=None, headless=False, parser_id=None):
    """Парсит LEMANAPRO, сохраняет ParsedProduct, архивирует старые цены и обновляет историю."""
    today = timezone.now().date()
    prod_obj = None
    if product_id:
        try:
            prod_obj = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            prod_obj = None
    else:
        prod_obj = Product.objects.filter(name__icontains=product_name).first()

    parser_obj = None
    if parser_id:
        try:
            from price_parser.models import ParserSchedule

            parser_obj = ParserSchedule.objects.get(pk=parser_id)
        except ParserSchedule.DoesNotExist:
            pass

    scraper = None
    try:
        scraper = LemanaProScraper(headless=headless)
        result = scraper.find_matching_products(product_name)

        if not result or not result.get("products"):
            print(f"Результаты парсинга не получены для {product_name}")
            update_product_price(prod_obj)
            return None

        for p in result["products"]:
            unit, pack_size = extract_unit_and_pack(p["name"])
            if not unit:
                unit = p.get("unit") or "шт"
            if not pack_size or pack_size == 0:
                pack_size = Decimal(1)

            parsed_obj, created = ParsedProduct.objects.update_or_create(
                product=prod_obj,
                url=p.get("url"),
                fetched_at__date=today,
                defaults={
                    "name": p["name"],
                    "price": p["price"],
                    "unit": unit,
                    "pack_size": pack_size,
                    "source": "lemanapro",
                    "owner": owner,
                    "parser": parser_obj,
                },
            )

            if not created and (parsed_obj.price != p["price"] or parsed_obj.pack_size != pack_size):
                try:
                    ParsedProductArchive.objects.create(
                        product=parsed_obj.product,
                        name=parsed_obj.name,
                        price=parsed_obj.price,
                        unit=parsed_obj.unit,
                        pack_size=parsed_obj.pack_size,
                        url=parsed_obj.url,
                        source=parsed_obj.source,
                        fetched_at=parsed_obj.fetched_at,
                    )
                except Exception:
                    pass
                parsed_obj.name = p["name"]
                parsed_obj.price = p["price"]
                parsed_obj.unit = unit
                parsed_obj.pack_size = pack_size
                parsed_obj.fetched_at = timezone.now()
                parsed_obj.save()

        update_product_price(prod_obj)
        return result

    except WebDriverException as e:
        if scraper and hasattr(scraper, "driver"):
            try:
                scraper.driver.save_screenshot(os.path.join(PARSED_DIR, f"webdriver_error_{product_name}.png"))
            except Exception:
                pass
        print(f"WebDriver ошибка: {e}")
        update_product_price(prod_obj)
        return None

    except Exception as e:
        if scraper and hasattr(scraper, "driver"):
            try:
                scraper.driver.save_screenshot(os.path.join(PARSED_DIR, f"error_{product_name}.png"))
            except Exception:
                pass
        print(f"Ошибка парсинга: {e}")
        update_product_price(prod_obj)
        return None

    finally:
        if scraper:
            scraper.close()

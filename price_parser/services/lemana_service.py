from decimal import Decimal
from django.utils import timezone
from price_parser.models import Product, ParsedProduct, ParsedProductArchive
from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack
from .lemana_parse import LemanaProScraper


def lemana_parse_saved(product_name: str, product_id: int = None, owner=None):
    """
    Парсит сайт, сохраняет ParsedProduct и обновляет Product.avg_price_lemanapro.
    Если product_id передан, обновляет конкретный Product; иначе пытается найти по name.
    """
    today = timezone.now().date()
    prod_obj = None
    if product_id:
        try:
            prod_obj = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            prod_obj = None
    else:
        prod_obj = Product.objects.filter(name__icontains=product_name).first()

    scraper = LemanaProScraper(headless=True)
    try:
        result = scraper.find_matching_products(product_name)
        if not result:
            return None

        for p in result["products"]:
            # получаем фасовку/единицу по названию
            unit, pack_size = extract_unit_and_pack(p["name"])
            if not unit:
                unit = p.get("unit") or "шт"
            if not pack_size or pack_size == 0:
                pack_size = Decimal(1)

            # создаём или обновляем ParsedProduct один раз в день
            parsed_obj, created = ParsedProduct.objects.update_or_create(
                product=prod_obj,
                url=p.get("url"),
                fetched_at__date=today,
                defaults={
                    'name': p["name"],
                    'price': p["price"],
                    'unit': unit,
                    'pack_size': pack_size,
                    'source': "lemanapro",
                    'owner': owner
                }
            )

            # если цена или фасовка изменилась и объект уже существовал — архивируем
            if not created:
                if parsed_obj.price != p["price"] or parsed_obj.pack_size != pack_size:
                    ParsedProductArchive.objects.create(
                        product=parsed_obj.product,
                        name=parsed_obj.name,
                        price=parsed_obj.price,
                        unit=parsed_obj.unit,
                        pack_size=parsed_obj.pack_size,
                        url=parsed_obj.url,
                        source=parsed_obj.source,
                        fetched_at=parsed_obj.fetched_at
                    )
                    parsed_obj.name = p["name"]
                    parsed_obj.price = p["price"]
                    parsed_obj.unit = unit
                    parsed_obj.pack_size = pack_size
                    parsed_obj.fetched_at = timezone.now()
                    parsed_obj.save()

        # обновляем среднюю цену в Product (если есть prod_obj)
        if prod_obj:
            all_pp = ParsedProduct.objects.filter(product=prod_obj)
            unit_prices = []
            for pp in all_pp:
                if pp.price is None:
                    continue
                ps = pp.pack_size or Decimal(1)
                unit_prices.append((pp.price / ps) if ps else pp.price)
            avg_price_per_unit = filtered_unique_mean(unit_prices)
            prod_obj.avg_price_lemanapro = avg_price_per_unit
            prod_obj.parsed = bool(all_pp.exists())
            prod_obj.save()

        return result.get("avg_price")
    finally:
        scraper.close()
# from decimal import Decimal
# from django.utils import timezone
# from price_parser.models import Product, ParsedProduct, ParsedProductArchive
# from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack
# from .lemana_parse import LemanaProScraper
#
# from decimal import Decimal
# from django.utils import timezone
# from price_parser.models import Product, ParsedProduct, ParsedProductArchive
# from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack, normalize_price_str
# from .lemana_parse import LemanaProScraper
#
# def lemana_parse_saved(product_name: str, product_id: int = None, owner=None):
#     """
#     Парсит сайт, сохраняет ParsedProduct и обновляет Product.avg_price_lemanapro.
#     Если product_id передан, обновляет конкретный Product; иначе пытается найти по name.
#     """
#     today = timezone.now().date()
#     prod_obj = None
#     if product_id:
#         try:
#             prod_obj = Product.objects.get(pk=product_id)
#         except Product.DoesNotExist:
#             prod_obj = None
#     else:
#         prod_obj = Product.objects.filter(name__icontains=product_name).first()
#
#     scraper = LemanaProScraper(headless=True)
#     try:
#         result = scraper.find_matching_products(product_name)
#         if not result:
#             return None
#
#         for p in result["products"]:
#             # получаем фасовку/единицу по названию
#             unit, pack_size = extract_unit_and_pack(p["name"])
#             if not unit:
#                 unit = p.get("unit") or "шт"
#             if not pack_size or pack_size == 0:
#                 pack_size = Decimal(1)
#
#             # есть ли уже такой ParsedProduct (по url)
#             existing = None
#             if p.get("url"):
#                 existing = ParsedProduct.objects.filter(url=p["url"]).first()
#                 fetched_at__date = today,
#                 defaults = {
#                     'name': p["name"],
#                     'price': p["price"],
#                     'unit': unit,
#                     'pack_size': pack_size,
#                     'source': "lemanapro",
#                     'owner': owner
#                 }
#             )
#
#             if existing:
#                 # если цена или фасовка изменились — архивируем
#                 if existing.price != p["price"] or (existing.pack_size != pack_size):
#                     ParsedProductArchive.objects.create(
#                         product=existing.product,
#                         name=existing.name,
#                         price=existing.price,
#                         unit=existing.unit,
#                         pack_size=existing.pack_size,
#                         url=existing.url,
#                         source=existing.source,
#                         fetched_at=existing.fetched_at
#                     )
#                     existing.name = p["name"]
#                     existing.price = p["price"]
#                     existing.unit = unit
#                     existing.pack_size = pack_size
#                     existing.fetched_at = timezone.now()
#                     existing.save()
#                 continue
#
#             # создаём новый ParsedProduct
#             ParsedProduct.objects.create(
#                 product=prod_obj,
#                 name=p["name"],
#                 price=p["price"],
#                 unit=unit,
#                 pack_size=pack_size,
#                 url=p.get("url"),
#                 source="lemanapro",
#                 owner=owner
#             )
#
#         # обновляем среднюю цену в Product (если есть prod_obj)
#         if prod_obj:
#             all_pp = ParsedProduct.objects.filter(product=prod_obj)
#             unit_prices = []
#             for pp in all_pp:
#                 if pp.price is None:
#                     continue
#                 ps = pp.pack_size or Decimal(1)
#                 unit_prices.append((pp.price / ps) if ps else pp.price)
#             avg_price_per_unit = filtered_unique_mean(unit_prices)
#             prod_obj.avg_price_lemanapro = avg_price_per_unit
#             prod_obj.parsed = bool(all_pp.exists())
#             prod_obj.save()
#
#         return result.get("avg_price")
#     finally:
#         scraper.close()
#
#
# # def lemana_parse_saved(product_name: str):
# #     today = timezone.now().date()
# #     prod_obj = Product.objects.filter(name__icontains=product_name).first()
# #
# #     scraper = LemanaProScraper(headless=True)
# #     try:
# #         result = scraper.find_matching_products(product_name)
# #         if not result:
# #             return None
# #
# #         for p in result["products"]:
# #             # Извлекаем фасовку и единицу
# #             unit, pack_size = extract_unit_and_pack(p["name"])
# #             if not unit:
# #                 unit = p.get("unit") or "шт."
# #             if not pack_size or pack_size == 0:
# #                 pack_size = Decimal(1)
# #
# #             existing = ParsedProduct.objects.filter(url=p["url"]).first()
# #             if existing:
# #                 if existing.price != p["price"] or existing.pack_size != pack_size:
# #                     # Создаём архив
# #                     ParsedProductArchive.objects.create(
# #                         product=existing.product,
# #                         name=existing.name,
# #                         price=existing.price,
# #                         unit=existing.unit,
# #                         pack_size=existing.pack_size,
# #                         url=existing.url,
# #                         source=existing.source,
# #                         fetched_at=existing.fetched_at
# #                     )
# #                     # Обновляем текущий
# #                     existing.name = p["name"]
# #                     existing.price = p["price"]
# #                     existing.unit = unit
# #                     existing.pack_size = pack_size
# #                     existing.fetched_at = timezone.now()
# #                     existing.save()
# #                 continue
# #
# #             # Создаём новый ParsedProduct
# #             ParsedProduct.objects.create(
# #                 product=prod_obj,
# #                 name=p["name"],
# #                 price=p["price"],
# #                 unit=unit,
# #                 pack_size=pack_size,
# #                 url=p["url"],
# #                 source="lemanapro"
# #             )
# #
# #         # Средняя цена с учётом фасовки (price / pack_size)
# #         all_pp = ParsedProduct.objects.filter(product=prod_obj)
# #         unit_prices = [(pp.price / pp.pack_size if pp.pack_size else pp.price) for pp in all_pp]
# #         avg_price_per_unit = filtered_unique_mean(unit_prices)
# #
# #         if prod_obj:
# #             prod_obj.avg_price_lemanapro = avg_price_per_unit
# #             prod_obj.parsed = True
# #             prod_obj.save()
# #
# #         return avg_price_per_unit
# #     finally:
# #         scraper.close()

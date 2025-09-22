import asyncio
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from price_parser.models import Product, ParsedProduct
from price_parser.utils.price_utils import filtered_unique_mean
from price_parser.services.lemana_parse import async_search_multiple_products

@shared_task
def parse_products_batch_task(product_ids: list[int]):
    """
    Batch Celery таск: парсинг нескольких продуктов одним браузером.
    """
    products = Product.objects.filter(id__in=product_ids)

    async def run_scraper(products_list):
        results_dict = await async_search_multiple_products([p.name for p in products_list])

        for product in products_list:
            product_results = results_dict.get(product.name)
            if not product_results or not product_results.get("products"):
                continue

            unique_items = []
            seen = set()
            for r in product_results["products"]:
                key = (r["name"].lower(), Decimal(r["price"]))
                if key not in seen:
                    seen.add(key)
                    unique_items.append(r)

            prices = [Decimal(r["price"]) for r in unique_items]
            if not prices:
                continue

            avg_price = filtered_unique_mean(prices, trim_pct=0.3)

            for r in unique_items:
                ParsedProduct.objects.create(
                    product=product,
                    name=r["name"],
                    price=Decimal(r["price"]),
                    unit=r.get("unit"),
                    url=r.get("url"),
                    source='lemanapro',
                    fetched_at=timezone.now()
                )

            if avg_price is not None:
                product.avg_price_lemanapro = Decimal(avg_price)
                product.save()

    asyncio.run(run_scraper(list(products)))




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



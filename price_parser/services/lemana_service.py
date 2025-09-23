from decimal import Decimal
from django.utils import timezone
from price_parser.models import Product, ParsedProduct, ParsedProductArchive
from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack
from .lemana_parse import LemanaProScraper

def lemana_parse_saved(product_name: str):
    today = timezone.now().date()
    prod_obj = Product.objects.filter(name__icontains=product_name).first()

    scraper = LemanaProScraper(headless=True)
    try:
        result = scraper.find_matching_products(product_name)
        if not result:
            return None

        for p in result["products"]:
            # Извлекаем фасовку и единицу
            unit, pack_size = extract_unit_and_pack(p["name"])
            if not unit:
                unit = p.get("unit") or "шт."
            if not pack_size or pack_size == 0:
                pack_size = Decimal(1)

            existing = ParsedProduct.objects.filter(url=p["url"]).first()
            if existing:
                if existing.price != p["price"] or existing.pack_size != pack_size:
                    # Создаём архив
                    ParsedProductArchive.objects.create(
                        product=existing.product,
                        name=existing.name,
                        price=existing.price,
                        unit=existing.unit,
                        pack_size=existing.pack_size,
                        url=existing.url,
                        source=existing.source,
                        fetched_at=existing.fetched_at
                    )
                    # Обновляем текущий
                    existing.name = p["name"]
                    existing.price = p["price"]
                    existing.unit = unit
                    existing.pack_size = pack_size
                    existing.fetched_at = timezone.now()
                    existing.save()
                continue

            # Создаём новый ParsedProduct
            ParsedProduct.objects.create(
                product=prod_obj,
                name=p["name"],
                price=p["price"],
                unit=unit,
                pack_size=pack_size,
                url=p["url"],
                source="lemanapro"
            )

        # Средняя цена с учётом фасовки (price / pack_size)
        all_pp = ParsedProduct.objects.filter(product=prod_obj)
        unit_prices = [(pp.price / pp.pack_size if pp.pack_size else pp.price) for pp in all_pp]
        avg_price_per_unit = filtered_unique_mean(unit_prices)

        if prod_obj:
            prod_obj.avg_price_lemanapro = avg_price_per_unit
            prod_obj.parsed = True
            prod_obj.save()

        return avg_price_per_unit
    finally:
        scraper.close()

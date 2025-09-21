from price_parser.management.commands.parse_lemana_pro import LemanaProScraper
from price_parser.models import Product, ParsedProduct
from price_parser.utils.price_utils import filtered_unique_mean
from django.utils import timezone
from decimal import Decimal

def parse_product(product_name: str):
    today = timezone.now().date()
    today_entries = ParsedProduct.objects.filter(name__icontains=product_name, fetched_at__date=today)
    if today_entries.exists():
        avg_price = filtered_unique_mean([p.price for p in today_entries], trim_pct=0.3)
        return avg_price

    scraper = LemanaProScraper(headless=True)
    try:
        result = scraper.find_matching_products(product_name)
        if not result:
            return None

        avg_price = result["avg_price"]
        for p in result["products"]:
            if not ParsedProduct.objects.filter(name=p["name"], fetched_at__date=today).exists():
                ParsedProduct.objects.create(
                    name=p["name"], price=p["price"], unit=p["unit"], url=p["url"], source="lemanapro"
                )

        try:
            prod_obj = Product.objects.get(name__icontains=product_name)
            prod_obj.avg_price_lemanapro = avg_price
            prod_obj.save()
        except Product.DoesNotExist:
            pass

        return avg_price
    finally:
        scraper.close()

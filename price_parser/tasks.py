# price_parser/tasks.py
from celery import shared_task
from decimal import Decimal
from .models import Product
from .services.lemana_pro_parser import LemanaProScraper
from .utils.price_utils import filtered_unique_mean

@shared_task
def parse_product_task(product_id):
    product = Product.objects.get(id=product_id)
    scraper = LemanaProScraper(headless=True)
    try:
        results = scraper.find_matching_products(product.name)
        if results:
            top10 = results[:10]
            prices = [Decimal(str(p['price'])) for p in top10]
            avg_price = filtered_unique_mean(prices)
            product.avg_price_lemanapro = avg_price or 0
            product.save()
    finally:
        scraper.close()


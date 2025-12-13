import os
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import undetected_chromedriver as uc
from django.utils import timezone

from price_parser.models import ParsedProduct, Product
from price_parser.utils.price_utils import filtered_unique_mean

PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)


class LemanaProScraper:
    BASE_URL = "https://lemanapro.ru/search/?q="

    def __init__(self, headless=False):
        options = uc.ChromeOptions()
        options.headless = headless
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        self.driver = uc.Chrome(options=options)

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def find_matching_products(self, product_name):
        query = " ".join(product_name.lower().split()[:3])
        url = self.BASE_URL + quote(query)
        self.driver.get(url)
        time.sleep(3)

        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
        time.sleep(2)

        products = []

        try:
            title_blocks = self.driver.find_elements("css selector", "div.c1gua8e6_plp")
            price_blocks = self.driver.find_elements("css selector", "div.p1otuot_plp")

            for title_block, price_block in zip(title_blocks[:20], price_blocks[:20]):  # топ-20
                try:
                    a_tag = title_block.find_element("css selector", 'a[data-qa="product-name"]')
                    name_span = a_tag.find_element("css selector", "span.product-card-name-link")
                    name = name_span.text.strip()
                    url = a_tag.get_attribute("href")
                    if not url.startswith("http"):
                        url = "https://lemanapro.ru" + url

                    price_text = price_block.find_element(
                        "css selector", 'span[data-qa="primary-price-main"]'
                    ).text.strip()
                    price_text = price_text.replace("\xa0", "").replace(" ", "")
                    price = Decimal(price_text)
                    unit = price_block.find_element("css selector", "span.p1yvm8ab_plp").text.strip()

                    products.append(
                        {
                            "name": name,
                            "price": price,
                            "unit": unit,
                            "url": url,
                        }
                    )

                except InvalidOperation:
                    pass
                except Exception:
                    pass

        except Exception:
            pass

        if not products:
            return None

        # Средняя цена
        prices = [p["price"] for p in products]
        avg_price = filtered_unique_mean(prices, trim_pct=0.3)
        return {"products": products, "avg_price": avg_price}


def parse_product(product_name: str):
    """
    Сервисная функция: парсит продукт, сохраняет в БД ParsedProduct, обновляет Product.avg_price_lemanapro
    """
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

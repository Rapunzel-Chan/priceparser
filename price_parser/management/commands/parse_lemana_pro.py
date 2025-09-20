# price_parser/management/commands/parse_lemana_pro.py

import os
import time
from decimal import Decimal
from urllib.parse import quote
from datetime import timedelta

import undetected_chromedriver as uc
from django.core.management.base import BaseCommand
from django.utils import timezone

from price_parser.utils.price_utils import filtered_unique_mean
from price_parser.models import ParsedProduct

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
        self.driver.quit()

    def find_matching_products(self, product_name):
        query = ' '.join(product_name.lower().split()[:3])
        url = self.BASE_URL + quote(query)
        print(f"🔎 Открываем страницу поиска: {url}")
        self.driver.get(url)
        time.sleep(4)

        products = []

        try:
            title_blocks = self.driver.find_elements("css selector", "div.c1gua8e6_plp")
            price_blocks = self.driver.find_elements("css selector", "div.p1otuot_plp")

            for title_block, price_block in zip(title_blocks[:10], price_blocks[:10]):  # топ-10
                a_tag = title_block.find_element("css selector", 'a[data-qa="product-name"]')
                name_span = a_tag.find_element("css selector", "span.product-card-name-link")
                name = name_span.text.strip()
                url = "https://lemanapro.ru" + a_tag.get_attribute("href")

                price_main = price_block.find_element("css selector", 'span[data-qa="primary-price-main"]').text.strip()
                price = Decimal(price_main.replace("\xa0", "").replace(" ", ""))

                unit = price_block.find_element("css selector", "span.p1yvm8ab_plp").text.strip()

                products.append({"name": name, "price": price, "unit": unit, "url": url})

        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")

        if not products:
            return None

        prices = [p["price"] for p in products]
        avg_price = filtered_unique_mean(prices, trim_pct=0.3)

        return {"products": products, "avg_price": avg_price}


class Command(BaseCommand):
    help = "Парсит товары LemanaPro"

    def add_arguments(self, parser):
        parser.add_argument("--product", type=str, required=True, help="Название продукта")

    def handle(self, *args, **options):
        product_name = options["product"]
        print(f"📦 Парсим с сайта: {product_name}")

        # Проверка в БД: есть ли свежие ParsedProduct (не старше 1 дня)
        one_day_ago = timezone.now() - timedelta(days=1)
        db_prices = ParsedProduct.objects.filter(
            name__icontains=product_name, fetched_at__gte=one_day_ago
        )

        if db_prices.exists():
            avg_price = filtered_unique_mean([p.price for p in db_prices], trim_pct=0.3)
            print(f"💾 Используем данные из БД: средняя цена {avg_price}")
            return

        # Если нет актуальных данных — парсим сайт
        scraper = LemanaProScraper(headless=False)
        try:
            result = scraper.find_matching_products(product_name)
            if not result:
                print(f"⚠️ Нет результатов для {product_name}")
                return

            avg_price = result["avg_price"]
            print(f"✅ Средняя цена: {avg_price}")

            # Сохраняем результаты в базу и файл
            for p in result["products"]:
                ParsedProduct.objects.create(
                    name=p["name"],
                    price=p["price"],
                    unit=p["unit"],
                    url=p["url"],
                    source="lemanapro"
                )

            filename = os.path.join(PARSED_DIR, f"{product_name}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                for p in result["products"]:
                    f.write(f"{p}\n")
            print(f"📁 Результаты сохранены в {filename}")

        finally:
            scraper.close()

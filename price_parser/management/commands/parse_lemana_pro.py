import os
import time
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

import undetected_chromedriver as uc
from django.core.management.base import BaseCommand
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from price_parser.models import ParsedProduct
from price_parser.utils.price_utils import extract_unit_and_pack, filtered_unique_mean, normalize_price_str

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
        query = " ".join(product_name.lower().split()[:4])
        url = self.BASE_URL + quote(query)
        print(f"Открываем страницу поиска: {url}")
        self.driver.get(url)

        # ждём появления результатов
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
                )
            )
        except Exception:
            print("Результаты не найдены")
            return None

        SCROLL_PAUSE_TIME = 1.0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(10):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        products = []

        title_blocks = self.driver.find_elements(
            By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card__title"
        )
        price_blocks_red = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='new-price-main']")
        price_blocks_black = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")
        unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[class*='product-carousel']:not([data-qa])")

        max_take = 10
        parsed_count = 0

        for i, title_block in enumerate(title_blocks[:max_take]):
            try:
                name = title_block.text.strip()
                url = title_block.get_attribute("href") or ""

                price_decimal = None
                if i < len(price_blocks_red):
                    price_text = price_blocks_red[i].text.strip()
                    price_decimal = normalize_price_str(price_text)
                if price_decimal is None and i < len(price_blocks_black):
                    price_text = price_blocks_black[i].text.strip()
                    price_decimal = normalize_price_str(price_text)

                if price_decimal is None:
                    print(f"Нет цены для товара: {name}")
                    continue

                unit, pack_size = extract_unit_and_pack(name)
                if i < len(unit_blocks):
                    unit_text = unit_blocks[i].text.strip()
                    if "шт" in unit_text:
                        unit = "шт"
                if not pack_size or pack_size == 0:
                    pack_size = Decimal(1)

                price_per_unit = (price_decimal / pack_size) if pack_size else price_decimal

                products.append(
                    {
                        "name": name,
                        "price": price_decimal,
                        "unit": unit,
                        "pack_size": pack_size,
                        "url": url,
                        "price_per_unit": price_per_unit,
                    }
                )
                parsed_count += 1
                print(f"Пропарсено: {name} — {price_decimal} {unit} (цена за единицу {price_per_unit})")

            except Exception as e:
                print(f"Ошибка при обработке товара: {e}")
                continue

        avg_price = None
        if products:
            unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
            avg_price = filtered_unique_mean(unit_prices)
            print(f"Средняя цена за единицу (filtered): {avg_price}")

        print(f"Всего пропарсено товаров: {parsed_count}")
        return {"products": products, "avg_price": avg_price}


class Command(BaseCommand):
    help = "Парсит товары LemanaPro"

    def add_arguments(self, parser):
        parser.add_argument("--product", type=str, required=True, help="Название продукта")

    def handle(self, *args, **options):
        product_name = options["product"]
        print(f"Парсим с сайта: {product_name}")

        one_day_ago = timezone.now() - timedelta(days=1)
        db_prices = ParsedProduct.objects.filter(name__icontains=product_name, fetched_at__gte=one_day_ago)

        if db_prices.exists():
            avg_price = filtered_unique_mean([p.price for p in db_prices])
            print(f"Используем данные из БД: средняя цена {avg_price}")
            return

        scraper = LemanaProScraper(headless=False)
        try:
            result = scraper.find_matching_products(product_name)
            if not result:
                print(f"Нет результатов для {product_name}")
                return

            avg_price = result["avg_price"]
            print(f"Средняя цена: {avg_price}")

            for p in result["products"]:
                ParsedProduct.objects.create(
                    name=p["name"], price=p["price"], unit=p["unit"], url=p["url"], source="lemanapro"
                )

            filename = os.path.join(PARSED_DIR, f"{product_name}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                for p in result["products"]:
                    f.write(f"{p}\n")
            print(f"Результаты сохранены в {filename}")

        finally:
            scraper.close()
            print("Закрыли браузер")

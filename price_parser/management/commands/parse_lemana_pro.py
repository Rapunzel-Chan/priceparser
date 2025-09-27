
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
import os
import time
from decimal import Decimal
from datetime import timedelta
from urllib.parse import quote
from django.core.management.base import BaseCommand
from django.utils import timezone
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

from price_parser.models import ParsedProduct
from price_parser.utils.price_utils import normalize_price_str, filtered_unique_mean, extract_unit_and_pack

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
        query = ' '.join(product_name.lower().split()[:4])
        url = self.BASE_URL + quote(query)
        print(f"🔎 Открываем страницу поиска: {url}")
        self.driver.get(url)

        # ждём появления результатов
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
                )
            )
        except Exception:
            print("⚠️ Результаты не найдены")
            return None

        # Скроллим страницу
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

        title_blocks = self.driver.find_elements(By.CSS_SELECTOR,
                                                 "a[data-qa='product-name'], a.product-name, .product-card__title")
        price_blocks_red = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='new-price-main']")
        price_blocks_black = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")
        unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[class*='product-carousel']:not([data-qa])")

        max_take = 10
        parsed_count = 0

        for i, title_block in enumerate(title_blocks[:max_take]):
            try:
                name = title_block.text.strip()
                url = title_block.get_attribute("href") or ""

                # Берём красную цену, если есть, иначе черную
                price_decimal = None
                if i < len(price_blocks_red):
                    price_text = price_blocks_red[i].text.strip()
                    price_decimal = normalize_price_str(price_text)
                if price_decimal is None and i < len(price_blocks_black):
                    price_text = price_blocks_black[i].text.strip()
                    price_decimal = normalize_price_str(price_text)

                if price_decimal is None:
                    print(f"⚠️ Нет цены для товара: {name}")
                    continue

                # Единица и фасовка
                unit, pack_size = extract_unit_and_pack(name)
                if i < len(unit_blocks):
                    unit_text = unit_blocks[i].text.strip()
                    if 'шт' in unit_text:
                        unit = 'шт'
                if not pack_size or pack_size == 0:
                    pack_size = Decimal(1)

                price_per_unit = (price_decimal / pack_size) if pack_size else price_decimal

                products.append({
                    "name": name,
                    "price": price_decimal,
                    "unit": unit,
                    "pack_size": pack_size,
                    "url": url,
                    "price_per_unit": price_per_unit
                })
                parsed_count += 1
                print(f"💰 Пропарсено: {name} — {price_decimal} {unit} (цена за единицу {price_per_unit})")

            except Exception as e:
                print(f"❌ Ошибка при обработке товара: {e}")
                continue

        avg_price = None
        if products:
            unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
            avg_price = filtered_unique_mean(unit_prices)
            print(f"📊 Средняя цена за единицу (filtered): {avg_price}")

        print(f"✅ Всего пропарсено товаров: {parsed_count}")
        return {"products": products, "avg_price": avg_price}


class Command(BaseCommand):
    help = "Парсит товары LemanaPro"

    def add_arguments(self, parser):
        parser.add_argument("--product", type=str, required=True, help="Название продукта")

    def handle(self, *args, **options):
        product_name = options["product"]
        print(f"📦 Парсим с сайта: {product_name}")

        one_day_ago = timezone.now() - timedelta(days=1)
        db_prices = ParsedProduct.objects.filter(
            name__icontains=product_name, fetched_at__gte=one_day_ago
        )

        if db_prices.exists():
            avg_price = filtered_unique_mean([p.price for p in db_prices])
            print(f"💾 Используем данные из БД: средняя цена {avg_price}")
            return

        scraper = LemanaProScraper(headless=False)
        try:
            result = scraper.find_matching_products(product_name)
            if not result:
                print(f"⚠️ Нет результатов для {product_name}")
                return

            avg_price = result["avg_price"]
            print(f"✅ Средняя цена: {avg_price}")

            # Сохраняем в БД
            for p in result["products"]:
                ParsedProduct.objects.create(
                    name=p["name"],
                    price=p["price"],
                    unit=p["unit"],
                    url=p["url"],
                    source="lemanapro"
                )

            # Сохраняем в файл
            filename = os.path.join(PARSED_DIR, f"{product_name}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                for p in result["products"]:
                    f.write(f"{p}\n")
            print(f"📁 Результаты сохранены в {filename}")

        finally:
            scraper.close()
            print("🔒 Закрыли браузер")


# PARSED_DIR = "parsed_products"
# os.makedirs(PARSED_DIR, exist_ok=True)
#
#
# class LemanaProScraper:
#     BASE_URL = "https://lemanapro.ru/search/?q="
#
#     def __init__(self, headless=False):
#         options = uc.ChromeOptions()
#         options.headless = headless
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("window-size=1920,1080")
#         options.add_argument(
#             "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
#         )
#         self.driver = uc.Chrome(options=options)
#
#     def close(self):
#         self.driver.quit()
#
#     def find_matching_products(self, product_name):
#         """
#         Возвращает dict:
#         {
#             "products": [
#                 {"name": ..., "price": Decimal(...), "unit": "шт", "pack_size": Decimal(...), "url": ... , "price_per_unit": Decimal(...)} ,
#                 ...
#             ],
#             "avg_price": Decimal(...)  # средняя цена за единицу (после нормализации и фильтрации)
#         }
#         """
#         from price_parser.utils.price_utils import normalize_price_str, filtered_unique_mean, extract_unit_and_pack
#         from decimal import Decimal
#         from urllib.parse import quote
#         from selenium.webdriver.common.by import By
#         from selenium.webdriver.support.ui import WebDriverWait
#         from selenium.webdriver.support import expected_conditions as EC
#         import time
#
#         query = ' '.join(product_name.lower().split()[:4])
#         url = self.BASE_URL + quote(query)
#         self.driver.get(url)
#
#         # ждём появления результатов
#         try:
#             WebDriverWait(self.driver, 15).until(
#                 EC.presence_of_element_located(
#                     (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
#                 )
#             )
#         except Exception:
#             return None
#
#         # скроллим для подгрузки всех товаров
#         SCROLL_PAUSE_TIME = 1.0
#         last_height = self.driver.execute_script("return document.body.scrollHeight")
#         for _ in range(10):
#             self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(SCROLL_PAUSE_TIME)
#             new_height = self.driver.execute_script("return document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height
#
#         products = []
#         title_blocks = self.driver.find_elements(By.CSS_SELECTOR,
#                                                  "a[data-qa='product-name'], a.product-name, .product-card__title")
#         price_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='new-price-main']")
#         unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[class*='product-carousel']:not([data-qa])")
#
#         max_take = 20
#         for i, title_block in enumerate(title_blocks[:max_take]):
#             try:
#                 name = title_block.text.strip()
#                 url = title_block.get_attribute("href") or ""
#
#                 # Цена
#                 price_decimal = None
#                 if i < len(price_blocks):
#                     price_text = price_blocks[i].text.strip()
#                     price_decimal = normalize_price_str(price_text)
#                 if price_decimal is None:
#                     continue  # пропускаем товар без цены
#
#                 # Единица и фасовка
#                 unit, pack_size = extract_unit_and_pack(name)
#                 if i < len(unit_blocks):
#                     unit_text = unit_blocks[i].text.strip()
#                     if 'шт' in unit_text:
#                         unit = 'шт'
#                 if not pack_size or pack_size == 0:
#                     pack_size = Decimal(1)
#
#                 price_per_unit = (price_decimal / pack_size) if pack_size else price_decimal
#
#                 products.append({
#                     "name": name,
#                     "price": price_decimal,
#                     "unit": unit,
#                     "pack_size": pack_size,
#                     "url": url,
#                     "price_per_unit": price_per_unit
#                 })
#
#             except Exception:
#                 continue
#
#         # Средняя цена за единицу (с фильтрацией)
#         unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
#         avg_price = filtered_unique_mean(unit_prices) if unit_prices else None
#
#         return {"products": products, "avg_price": avg_price}
#
#     # def find_matching_products(self, product_name):
#     #     query = ' '.join(product_name.lower().split()[:3])
#     #     url = self.BASE_URL + quote(query)
#     #     print(f"🔎 Открываем страницу поиска: {url}")
#     #     self.driver.get(url)
#     #     time.sleep(4)  # стартовая пауза для загрузки
#     #
#     #     # Прокрутка страницы для подгрузки всех товаров
#     #     SCROLL_PAUSE_TIME = 2
#     #     last_height = self.driver.execute_script("return document.body.scrollHeight")
#     #
#     #     while True:
#     #         self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#     #         time.sleep(SCROLL_PAUSE_TIME)
#     #         new_height = self.driver.execute_script("return document.body.scrollHeight")
#     #         if new_height == last_height:
#     #             break
#     #         last_height = new_height
#     #
#     #     products = []
#     #
#     #     try:
#     #         title_blocks = self.driver.find_elements("css selector", "div.c1gua8e6_plp")
#     #         price_blocks = self.driver.find_elements("css selector", "div.p1otuot_plp")
#     #
#     #         for title_block, price_block in zip(title_blocks, price_blocks):
#     #             a_tag = title_block.find_element("css selector", 'a[data-qa="product-name"]')
#     #             name_span = a_tag.find_element("css selector", "span.product-card-name-link")
#     #             name = name_span.text.strip()
#     #             url = "https://lemanapro.ru" + a_tag.get_attribute("href")
#     #
#     #             price_main = price_block.find_element("css selector", 'span[data-qa="primary-price-main"]').text.strip()
#     #             price = Decimal(price_main.replace("\xa0", "").replace(" ", "").replace(",", "."))
#     #
#     #             unit = price_block.find_element("css selector", "span.p1yvm8ab_plp").text.strip()
#     #
#     #             products.append({"name": name, "price": price, "unit": unit, "url": url})
#     #             print(f"💰 Пропарсено: {name} — {price} {unit}")
#     #
#     #             if len(products) >= 15:  # останавливаем после 15 товаров
#     #                 break
#     #
#     #     except Exception as e:
#     #         print(f"❌ Ошибка парсинга: {e}")
#     #
#     #     if not products:
#     #         return None
#     #
#     #     prices = [p["price"] for p in products]
#     #     avg_price = filtered_unique_mean(prices, trim_pct=0.3)
#     #
#     #     return {"products": products, "avg_price": avg_price}
#
#
# class Command(BaseCommand):
#     help = "Парсит товары LemanaPro"
#
#     def add_arguments(self, parser):
#         parser.add_argument("--product", type=str, required=True, help="Название продукта")
#
#     def handle(self, *args, **options):
#         product_name = options["product"]
#         print(f"📦 Парсим с сайта: {product_name}")
#
#         # Проверка в БД: есть ли свежие ParsedProduct (не старше 1 дня)
#         one_day_ago = timezone.now() - timedelta(days=1)
#         db_prices = ParsedProduct.objects.filter(
#             name__icontains=product_name, fetched_at__gte=one_day_ago
#         )
#
#         if db_prices.exists():
#             avg_price = filtered_unique_mean([p.price for p in db_prices], trim_pct=0.3)
#             print(f"💾 Используем данные из БД: средняя цена {avg_price}")
#             return
#
#         # Если нет актуальных данных — парсим сайт
#         scraper = LemanaProScraper(headless=False)
#         try:
#             result = scraper.find_matching_products(product_name)
#             if not result:
#                 print(f"⚠️ Нет результатов для {product_name}")
#                 return
#
#             avg_price = result["avg_price"]
#             print(f"✅ Средняя цена: {avg_price}")
#
#             # Сохраняем результаты в базу и файл
#             for p in result["products"]:
#                 ParsedProduct.objects.create(
#                     name=p["name"],
#                     price=p["price"],
#                     unit=p["unit"],
#                     url=p["url"],
#                     source="lemanapro"
#                 )
#
#             filename = os.path.join(PARSED_DIR, f"{product_name}.txt")
#             with open(filename, "w", encoding="utf-8") as f:
#                 for p in result["products"]:
#                     f.write(f"{p}\n")
#             print(f"📁 Результаты сохранены в {filename}")
#
#         finally:
#             scraper.close()

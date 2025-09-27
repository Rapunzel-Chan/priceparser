import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack
from price_parser.models import ParsedProduct

# PARSED_DIR = "parsed_products"
# os.makedirs(PARSED_DIR, exist_ok=True)

import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack
from price_parser.models import ParsedProduct

# PARSED_DIR = "parsed_products"
# os.makedirs(PARSED_DIR, exist_ok=True)

import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack, normalize_price_str, filtered_unique_mean
from price_parser.models import ParsedProduct

import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack, normalize_price_str, filtered_unique_mean

import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack, normalize_price_str, filtered_unique_mean

PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)

class LemanaProScraper:
    BASE_URL = "https://lemanapro.ru/search/?q="

    def __init__(self, headless=False):
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")  # современный headless
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("window-size=1920,1080")

        self.driver = uc.Chrome(options=options)

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def find_matching_products(self, product_name, max_items=20):
        query = ' '.join(product_name.lower().split()[:4])
        url = self.BASE_URL + quote(query)
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
                )
            )
        except Exception:
            self.driver.save_screenshot(os.path.join(PARSED_DIR, f"timeout_{product_name}.png"))
            return None

        # Скроллим страницу для подгрузки контента
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
        # Селекторы для карточек
        title_blocks = self.driver.find_elements(
            By.CSS_SELECTOR,
            "a[data-qa='product-name'], a.product-name, .product-card__title, a"
        )
        price_blocks = self.driver.find_elements(
            By.CSS_SELECTOR,
            "span[data-qa='primary-price-main'], .price, .product-card__price, .price__value"
        )

        for i, title_block in enumerate(title_blocks[:max_items]):
            try:
                name = title_block.text.strip()
                url = title_block.get_attribute("href") or ""

                price_text = None
                if i < len(price_blocks):
                    price_text = price_blocks[i].text.strip()
                else:
                    # fallback: пробуем внутри карточки
                    try:
                        parent = title_block.find_element(By.XPATH, "./ancestor::div[1]")
                        price_el = parent.find_element(By.CSS_SELECTOR,
                                                       "span[data-qa='primary-price-main'], .price, .product-card__price")
                        price_text = price_el.text.strip()
                    except Exception:
                        price_text = ""

                price_decimal = normalize_price_str(price_text)
                if price_decimal is None:
                    continue

                unit, pack_size = extract_unit_and_pack(name)
                if not pack_size or pack_size == 0:
                    pack_size = Decimal(1)

                price_per_unit = price_decimal / pack_size

                products.append({
                    "name": name,
                    "price": price_decimal,
                    "unit": unit,
                    "pack_size": pack_size,
                    "url": url,
                    "price_per_unit": price_per_unit
                })
            except Exception:
                continue

        unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
        avg_price = filtered_unique_mean(unit_prices) if unit_prices else None

        return {"products": products, "avg_price": avg_price}



# class LemanaProScraper:
#     BASE_URL = "https://lemanapro.ru/search/?q="
#
#     def __init__(self, headless=True):
#         import undetected_chromedriver as uc
#         options = uc.ChromeOptions()
#         options.headless = headless
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("window-size=1920,1080")
#         self.driver = uc.Chrome(options=options)
#
#     def close(self):
#         try:
#             self.driver.quit()
#         except Exception:
#             pass
#
#     def find_matching_products(self, product_name):
#         query = ' '.join(product_name.lower().split()[:3])
#         url = self.BASE_URL + quote(query)
#         self.driver.get(url)
#
#         try:
#             WebDriverWait(self.driver, 15).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-qa='product-name']"))
#             )
#         except:
#             return None
#
#         SCROLL_PAUSE_TIME = 2
#         last_height = self.driver.execute_script("return document.body.scrollHeight")
#         while True:
#             self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(SCROLL_PAUSE_TIME)
#             new_height = self.driver.execute_script("return document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height
#
#         products = []
#         title_blocks = self.driver.find_elements(By.CSS_SELECTOR, "a[data-qa='product-name']")
#         price_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")
#         unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span.p1yvm8ab_plp")
#
#         for i, title_block in enumerate(title_blocks[:15]):
#             try:
#                 name = title_block.text.strip()
#                 url = title_block.get_attribute("href")
#                 price_text = price_blocks[i].text.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
#                 price = Decimal(price_text)
#                 unit, pack_size = extract_unit_and_pack(unit_blocks[i].text.strip() if i < len(unit_blocks) else name)
#                 products.append({"name": name, "price": price, "unit": unit, "pack_size": pack_size, "url": url})
#             except Exception:
#                 continue
#
#         avg_price = sum(p["price"] for p in products) / len(products) if products else None
#         return {"products": products, "avg_price": avg_price}


# class LemanaProScraper:
#     BASE_URL = "https://lemanapro.ru/search/?q="
#
#     def __init__(self, headless=True):
#         import undetected_chromedriver as uc
#         options = uc.ChromeOptions()
#         options.headless = headless
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("window-size=1920,1080")
#         self.driver = uc.Chrome(options=options)
#
#     def close(self):
#         try:
#             self.driver.quit()
#         except Exception:
#             pass
#
#     def find_matching_products(self, product_name):
#         query = ' '.join(product_name.lower().split()[:3])
#         url = self.BASE_URL + quote(query)
#         self.driver.get(url)
#
#         try:
#             WebDriverWait(self.driver, 15).until(
#                 EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-qa='product-name']"))
#             )
#         except:
#             return None
#
#         SCROLL_PAUSE_TIME = 2
#         last_height = self.driver.execute_script("return document.body.scrollHeight")
#         while True:
#             self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(SCROLL_PAUSE_TIME)
#             new_height = self.driver.execute_script("return document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height
#
#         products = []
#         title_blocks = self.driver.find_elements(By.CSS_SELECTOR, "a[data-qa='product-name']")
#         price_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")
#         unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span.p1yvm8ab_plp")
#
#         for i, title_block in enumerate(title_blocks[:15]):
#             try:
#                 name = title_block.text.strip()
#                 url = title_block.get_attribute("href")
#                 price_text = price_blocks[i].text.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
#                 price = Decimal(price_text)
#                 unit, pack_size = extract_unit_and_pack(unit_blocks[i].text.strip() if i < len(unit_blocks) else name)
#                 products.append({"name": name, "price": price, "unit": unit, "pack_size": pack_size, "url": url})
#             except Exception:
#                 continue
#
#         avg_price = sum(p["price"] for p in products) / len(products) if products else None
#         return {"products": products, "avg_price": avg_price}

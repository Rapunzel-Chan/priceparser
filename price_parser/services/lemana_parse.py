import os
import re
import time
from decimal import Decimal
from urllib.parse import quote

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from price_parser.utils.price_utils import extract_unit_and_pack, normalize_price_str

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

    def find_matching_products(self, product_name, max_items=10):
        query = " ".join(product_name.lower().split()[:4])
        url = self.BASE_URL + quote(query)
        print(f"Открываем страницу поиска: {url}")
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
                )
            )
        except Exception:
            print("Результаты не найдены")
            return None

        self._scroll_page()

        html_file = os.path.join(PARSED_DIR, f"page_{product_name.replace(' ', '_')}.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)

        products = []

        title_blocks = self.driver.find_elements(
            By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card__title"
        )
        price_blocks_red = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='new-price-main']")
        price_blocks_black = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")

        max_take = min(max_items, len(title_blocks))
        parsed_count = 0

        for i in range(max_take):
            try:
                name = title_blocks[i].text.strip()
                url = title_blocks[i].get_attribute("href") or ""

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

                print(f"Отладка: название='{name}', определенная фасовка={pack_size} {unit}")

                if pack_size == 1 or unit == "шт":

                    unit_blocks = self.driver.find_elements(
                        By.CSS_SELECTOR, "span[class*='product-carousel']:not([data-qa])"
                    )
                    if i < len(unit_blocks):
                        unit_text = unit_blocks[i].text.strip()
                        print(f"Отладка: unit_blocks текст='{unit_text}'")

                        unit_match = re.search(r"(\d+)\s*(пар|шт)", unit_text.lower())
                        if unit_match:
                            pack_size = Decimal(unit_match.group(1))
                            unit = "пар" if unit_match.group(2) == "пар" else "шт"
                            print(f"Отладка: фасовка из unit_blocks={pack_size} {unit}")

                price_per_unit = (price_decimal / pack_size) if pack_size and pack_size > 0 else price_decimal

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

                print(
                    f"Пропарсено: {name} — {price_decimal} руб. (фасовка: {pack_size} {unit}, "
                    f"цена за единицу: {price_per_unit} руб./ {unit})"
                )

            except Exception as e:
                print(f"Ошибка при обработке товара: {e}")
                continue

        print(f"Всего пропарсено товаров: {parsed_count}")
        return {"products": products, "avg_price": None}

    def _scroll_page(self):
        SCROLL_PAUSE = 1.0
        last_h = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE)
            new_h = self.driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h

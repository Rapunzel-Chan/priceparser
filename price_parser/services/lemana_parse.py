import os
import time
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack
from price_parser.models import ParsedProduct


import os
import time
import json
import re
from decimal import Decimal
from urllib.parse import quote
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from price_parser.utils.price_utils import extract_unit_and_pack, filtered_unique_mean

PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)

class LemanaProScraper:
    BASE_URL = "https://lemanapro.ru/search/?q="

    def __init__(self, headless=False):
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
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
        print(f"[INFO] Запрос: {query}")
        print(f"[INFO] URL: {url}")

        self.driver.get(url)

        # Ждём загрузки скриптов на странице
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "script"))
            )
        except Exception as e:
            print(f"[WARN] Таймаут ожидания загрузки страницы: {e}")

        time.sleep(1)
        self._scroll_page()

        # Сохраняем HTML для отладки
        html_file = os.path.join(PARSED_DIR, f"page_{product_name.replace(' ', '_')}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)

        # Получаем JSON с товарами
        products_json = self._extract_products_json()
        if not products_json:
            print("[ERROR] Не найдено JSON с товарами на странице")
            return None

        products = []
        for prod in products_json[:max_items]:
            try:
                name = prod.get("displayedName", "")
                url = "https://www.lemanapro.ru" + prod.get("productLink", "")
                price_val = prod.get("price", {}).get("main_price")
                brand = prod.get("brand")

                if not price_val:
                    continue
                price_decimal = Decimal(price_val)

                # Извлекаем unit и pack_size
                unit, pack_size = extract_unit_and_pack(name)
                if not pack_size or pack_size == 0:
                    pack_size = Decimal(1)
                price_per_unit = price_decimal / pack_size

                products.append({
                    "name": name,
                    "url": url,
                    "price": price_decimal,
                    "unit": unit,
                    "pack_size": pack_size,
                    "price_per_unit": price_per_unit,
                    "brand": brand
                })

            except Exception as e:
                print(f"[WARN] Ошибка при обработке товара '{prod.get('displayedName')}': {e}")
                continue

        if not products:
            print("[ERROR] Ни один товар не распарсен.")
            return None

        unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
        avg_price = filtered_unique_mean(unit_prices) if unit_prices else None
        print(f"[RESULT] Найдено {len(products)} товаров, средняя цена за ед.: {avg_price}")

        return {
            "products": products,
            "avg_price": avg_price
        }

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

    def _extract_products_json(self):
        scripts = self.driver.find_elements(By.TAG_NAME, "script")
        for script in scripts:
            try:
                text = script.get_attribute("innerHTML")
                if "productsData" in text:
                    start = text.index('{"productsData"')
                    end = text.rindex('}') + 1
                    json_str = text[start:end]
                    data = json.loads(json_str)
                    return data.get("productsData", [])
            except Exception:
                continue
        return []

# Пример использования
if __name__ == "__main__":
    scraper = LemanaProScraper(headless=True)
    try:
        result = scraper.find_matching_products("Перчатки строительные", max_items=10)
        if result:
            for p in result["products"]:
                print(p)
    finally:
        scraper.close()

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

# import os
# import time
# from decimal import Decimal
# from urllib.parse import quote
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from price_parser.utils.price_utils import extract_unit_and_pack, normalize_price_str, filtered_unique_mean
#
#
# class LemanaProScraper:
#     BASE_URL = "https://lemanapro.ru/search/?q="
#     PARSED_DIR = "parsed_products"  # Определяем как атрибут класса
#
#     def __init__(self, headless=False):
#         import undetected_chromedriver as uc
#
#         # Убедимся, что папка существует при инициализации
#         os.makedirs(self.PARSED_DIR, exist_ok=True)
#
#         options = uc.ChromeOptions()
#         if headless:
#             options.add_argument("--headless=new")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("window-size=1920,1080")
#
#         self.driver = uc.Chrome(options=options)
#
#     def close(self):
#         try:
#             self.driver.quit()
#         except Exception:
#             pass
#
#     def find_matching_products(self, product_name, max_items=20):
#         query = ' '.join(product_name.lower().split()[:4])
#         url = self.BASE_URL + quote(query)
#         print(f"Запрос: {query}")
#         print(f"URL: {url}")
#
#         try:
#             self.driver.get(url)
#         except Exception as e:
#             print(f"Ошибка при загрузке страницы: {e}")
#             return None
#
#         # Ждем загрузки страницы
#         time.sleep(3)
#
#         # Сохраняем HTML-код страницы для анализа
#         try:
#             html_file = os.path.join(self.PARSED_DIR, f"page_{product_name.replace(' ', '_')}.html")
#             with open(html_file, 'w', encoding='utf-8') as f:
#                 f.write(self.driver.page_source)
#             print(f"HTML-код страницы сохранен в: {html_file}")
#         except Exception as e:
#             print(f"Ошибка при сохранении HTML-кода страницы: {e}")
#
#         # Проверяем, есть ли результаты
#         try:
#             # Сначала проверим, есть ли сообщение о том, что ничего не найдено
#             no_results_selectors = [
#                 ".search-no-results",
#                 ".no-results",
#                 "[class*='no-results']",
#                 ".not-found",
#                 "[class*='not-found']"
#             ]
#
#             for selector in no_results_selectors:
#                 try:
#                     no_results = self.driver.find_elements(By.CSS_SELECTOR, selector)
#                     if no_results:
#                         print(f"Найдено сообщение о отсутствии результатов: {selector}")
#                         return None
#                 except Exception:
#                     continue
#         except Exception as e:
#             print(f"Ошибка при проверке отсутствия результатов: {e}")
#
#         # Пробуем несколько вариантов ожидания элементов
#         selectors_to_try = [
#             (By.CSS_SELECTOR, ".product-card"),
#             (By.CSS_SELECTOR, "[class*='product-card']"),
#             (By.CSS_SELECTOR, ".product-item"),
#             (By.CSS_SELECTOR, "[class*='product-item']"),
#             (By.CSS_SELECTOR, ".snigxkz_plp"),
#             (By.CSS_SELECTOR, "[class*='snigxkz']"),
#             (By.CSS_SELECTOR, ".c2a98bi_plp"),
#             (By.CSS_SELECTOR, "[class*='c2a98bi']"),
#             (By.CSS_SELECTOR, "div[data-qa='product-card']"),
#             (By.CSS_SELECTOR, "div[class*='product-card']"),
#             (By.CSS_SELECTOR, "div[data-qa='product']"),
#             (By.CSS_SELECTOR, "div[class*='product']"),
#         ]
#
#         product_cards = None
#         for selector in selectors_to_try:
#             try:
#                 WebDriverWait(self.driver, 10).until(
#                     EC.presence_of_element_located(selector)
#                 )
#                 product_cards = self.driver.find_elements(selector[0], selector[1])
#                 if product_cards:
#                     print(f"Найдено элементов с селектором {selector}: {len(product_cards)}")
#                     break
#             except Exception as e:
#                 print(f"Селектор {selector} не сработал: {e}")
#                 continue
#
#         if not product_cards:
#             # Делаем скриншот для отладки
#             try:
#                 screenshot_file = os.path.join(self.PARSED_DIR, f"no_elements_{product_name.replace(' ', '_')}.png")
#                 self.driver.save_screenshot(screenshot_file)
#                 print(f"Не удалось найти элементы товара на странице. Скриншот сохранен: {screenshot_file}")
#             except Exception as e:
#                 print(f"Ошибка при сохранении скриншота: {e}")
#
#             # Дополнительно сохраняем HTML-код всей страницы
#             try:
#                 print("HTML-код страницы (первые 2000 символов):")
#                 print(self.driver.page_source[:2000])  # Первые 2000 символов
#             except Exception as e:
#                 print(f"Ошибка при получении HTML-кода: {e}")
#
#             return None
#
#         # Скроллим страницу для подгрузки контента
#         SCROLL_PAUSE_TIME = 1.0
#         last_height = self.driver.execute_script("return document.body.scrollHeight")
#         for _ in range(5):
#             self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#             time.sleep(SCROLL_PAUSE_TIME)
#             new_height = self.driver.execute_script("return document.body.scrollHeight")
#             if new_height == last_height:
#                 break
#             last_height = new_height
#
#         products = []
#
#         for i, card in enumerate(product_cards[:max_items]):
#             try:
#                 # Сохраняем HTML карточки для анализа
#                 try:
#                     card_html = card.get_attribute('outerHTML')
#                     card_file = os.path.join(self.PARSED_DIR, f"card_{i}_{product_name.replace(' ', '_')}.html")
#                     with open(card_file, 'w', encoding='utf-8') as f:
#                         f.write(card_html)
#                     print(f"HTML карточки {i} сохранен в: {card_file}")
#                 except Exception as e:
#                     print(f"Ошибка при сохранении HTML карточки {i}: {e}")
#
#                 # Извлекаем название товара
#                 name = self._extract_product_name(card)
#                 if not name:
#                     print(f"Не удалось извлечь название для карточки {i}")
#                     continue
#
#                 # Извлекаем URL
#                 url = self._extract_product_url(card)
#
#                 # Извлекаем цену
#                 price_text = self._extract_product_price(card)
#                 if not price_text:
#                     print(f"Не удалось извлечь цену для карточки {i}: {name}")
#                     continue
#
#                 price_decimal = normalize_price_str(price_text)
#                 if price_decimal is None:
#                     print(f"Не удалось преобразовать цену для карточки {i}: {price_text}")
#                     continue
#
#                 unit, pack_size = extract_unit_and_pack(name)
#                 if not pack_size or pack_size == 0:
#                     pack_size = Decimal(1)
#
#                 price_per_unit = price_decimal / pack_size
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
#                 print(f"Добавлен товар: {name}, цена: {price_decimal}")
#
#             except Exception as e:
#                 print(f"Ошибка при обработке карточки товара {i}: {e}")
#                 continue
#
#         if not products:
#             print("Не удалось извлечь данные ни из одной карточки")
#             return None
#
#         unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
#         avg_price = filtered_unique_mean(unit_prices) if unit_prices else None
#
#         print(f"Найдено товаров: {len(products)}, средняя цена: {avg_price}")
#         return {"products": products, "avg_price": avg_price}
#
#     def _extract_product_name(self, card):
#         """Извлекает название товара из карточки"""
#         selectors = [
#             ".product-card-name-link",
#             "[class*='product-card-name']",
#             ".zlBZQiMDi3_plp",
#             "[class*='zlBZQiMDi3_plp']",
#             ".product-name",
#             "[class*='product-name']",
#             "a[href*='/product/']",
#             "span[data-qa='product-name']",
#             "[data-qa='product-name']"
#         ]
#
#         for selector in selectors:
#             try:
#                 elements = card.find_elements(By.CSS_SELECTOR, selector)
#                 for element in elements:
#                     text = element.text.strip()
#                     if text and len(text) > 5:  # Проверяем, что текст не пустой и не слишком короткий
#                         print(f"Найдено название с селектором {selector}: {text}")
#                         return text
#             except Exception as e:
#                 print(f"Ошибка при извлечении названия с селектором {selector}: {e}")
#                 continue
#
#         # Если не нашли через селекторы, попробуем найти по тексту
#         try:
#             # Ищем все текстовые узлы в карточке
#             text_elements = card.find_elements(By.XPATH, ".//text()")
#             for element in text_elements:
#                 text = element.strip()
#                 if text and len(
#                         text) > 10 and not text.isdigit():  # Проверяем, что текст не пустой, не слишком короткий и не состоит только из цифр
#                     print(f"Найдено название через текст: {text}")
#                     return text
#         except Exception as e:
#             print(f"Ошибка при извлечении названия через текст: {e}")
#
#         return ""
#
#     def _extract_product_url(self, card):
#         """Извлекает URL товара из карточки"""
#         try:
#             link_element = card.find_element(By.CSS_SELECTOR, "a[href*='/product/']")
#             url = link_element.get_attribute("href")
#             print(f"Найден URL: {url}")
#             return url or ""
#         except Exception as e:
#             print(f"Ошибка при извлечении URL: {e}")
#             return ""
#
#     def _extract_product_price(self, card):
#         """Извлекает цену товара из карточки, обрабатывая разные форматы"""
#         # Список возможных селекторов для цены
#         price_selectors = [
#             "span[data-qa='primary-price-main']",
#             "span[data-qa='new-price-main']",
#             "span[data-qa='old-price-main']",
#             ".m1dfv26r_plp",
#             "[class*='m1dfv26r_plp']",
#             ".price",
#             "[class*='price']",
#             ".snigxkz_plp span",
#             "[class*='snigxkz_plp'] span",
#             ".c2a98bi_plp span",
#             "[class*='c2a98bi_plp'] span",
#             "[data-qa='product-primary-price'] span",
#             "[data-qa='product-old-new-price'] span"
#         ]
#
#         for selector in price_selectors:
#             try:
#                 price_elements = card.find_elements(By.CSS_SELECTOR, selector)
#                 for element in price_elements:
#                     text = element.text.strip()
#                     print(f"Найден текст с селектором {selector}: {text}")
#                     # Проверяем, что текст содержит цифры и возможно символы валюты
#                     if any(char.isdigit() for char in text):
#                         # Очищаем текст от лишних символов
#                         clean_text = ''.join(filter(lambda x: x.isdigit() or x == ',' or x == '.', text))
#                         if clean_text:
#                             print(f"Очищенная цена: {clean_text}")
#                             return clean_text
#             except Exception as e:
#                 print(f"Ошибка при извлечении цены с селектором {selector}: {e}")
#                 continue
#
#         # Если не нашли через селекторы, попробуем найти по тексту с цифрами
#         try:
#             # Ищем все текстовые узлы в карточке
#             text_elements = card.find_elements(By.XPATH, ".//text()")
#             for element in text_elements:
#                 text = element.strip()
#                 # Проверяем, что текст содержит цифры и возможно символы валюты
#                 if any(char.isdigit() for char in text) and ('₽' in text or 'руб' in text.lower()):
#                     # Очищаем текст от лишних символов
#                     clean_text = ''.join(filter(lambda x: x.isdigit() or x == ',' or x == '.', text))
#                     if clean_text:
#                         print(f"Найдена цена через текст: {clean_text}")
#                         return clean_text
#         except Exception as e:
#             print(f"Ошибка при извлечении цены через текст: {e}")
#
#         return ""

# class LemanaProScraper:
#     BASE_URL = "https://lemanapro.ru/search/?q="
#
#     def __init__(self, headless=False):
#         import undetected_chromedriver as uc
#
#         options = uc.ChromeOptions()
#         if headless:
#             options.add_argument("--headless=new")  # современный headless
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-dev-shm-usage")
#         options.add_argument("window-size=1920,1080")
#
#         self.driver = uc.Chrome(options=options)
#
#     def close(self):
#         try:
#             self.driver.quit()
#         except Exception:
#             pass
#
#     def find_matching_products(self, product_name, max_items=20):
#         query = ' '.join(product_name.lower().split()[:4])
#         url = self.BASE_URL + quote(query)
#         self.driver.get(url)
#
#         try:
#             WebDriverWait(self.driver, 15).until(
#                 EC.presence_of_element_located(
#                     (By.CSS_SELECTOR, "a[data-qa='product-name'], a.product-name, .product-card")
#                 )
#             )
#         except Exception:
#             self.driver.save_screenshot(os.path.join(PARSED_DIR, f"timeout_{product_name}.png"))
#             return None
#
#         # Скроллим страницу для подгрузки контента
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
#         # Селекторы для карточек
#         title_blocks = self.driver.find_elements(
#             By.CSS_SELECTOR,
#             "a[data-qa='product-name'], a.product-name, .product-card__title, a"
#         )
#         price_blocks = self.driver.find_elements(
#             By.CSS_SELECTOR,
#             "span[data-qa='primary-price-main'], .price, .product-card__price, .price__value"
#         )
#
#         for i, title_block in enumerate(title_blocks[:max_items]):
#             try:
#                 name = title_block.text.strip()
#                 url = title_block.get_attribute("href") or ""
#
#                 price_text = None
#                 if i < len(price_blocks):
#                     price_text = price_blocks[i].text.strip()
#                 else:
#                     # fallback: пробуем внутри карточки
#                     try:
#                         parent = title_block.find_element(By.XPATH, "./ancestor::div[1]")
#                         price_el = parent.find_element(By.CSS_SELECTOR,
#                                                        "span[data-qa='primary-price-main'], .price, .product-card__price")
#                         price_text = price_el.text.strip()
#                     except Exception:
#                         price_text = ""
#
#                 price_decimal = normalize_price_str(price_text)
#                 if price_decimal is None:
#                     continue
#
#                 unit, pack_size = extract_unit_and_pack(name)
#                 if not pack_size or pack_size == 0:
#                     pack_size = Decimal(1)
#
#                 price_per_unit = price_decimal / pack_size
#
#                 products.append({
#                     "name": name,
#                     "price": price_decimal,
#                     "unit": unit,
#                     "pack_size": pack_size,
#                     "url": url,
#                     "price_per_unit": price_per_unit
#                 })
#             except Exception:
#                 continue
#
#         unit_prices = [p["price_per_unit"] for p in products if p.get("price_per_unit") is not None]
#         avg_price = filtered_unique_mean(unit_prices) if unit_prices else None
#
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
#
#
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

import os
import time
from decimal import Decimal
from urllib.parse import quote

import undetected_chromedriver as uc
from price_parser.utils.price_utils import filtered_unique_mean
from price_parser.models import ParsedProduct

PARSED_DIR = "parsed_products"
os.makedirs(PARSED_DIR, exist_ok=True)

from urllib.parse import quote
from decimal import Decimal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from price_parser.models import ParsedProduct

class LemanaProScraper:
    BASE_URL = "https://lemanapro.ru/search/?q="

    def __init__(self, headless=True):
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.headless = headless
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("window-size=1920,1080")
        options.add_argument("--remote-debugging-port=9222")

        driver_path = r"C:\Users\rapun\PycharmProjects\Average_price_parser\chromedriver-win64\chromedriver.exe"
        self.driver = uc.Chrome(options=options, driver_executable_path=driver_path)

    def close(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def find_matching_products(self, product_name):
        query = ' '.join(product_name.lower().split()[:3])
        url = self.BASE_URL + quote(query)
        print(f"🔎 Открываем страницу поиска: {url}")

        try:
            self.driver.get(url)
        except Exception as e:
            print(f"❌ Не удалось открыть страницу: {e}")
            return None

        # Ожидание подгрузки хотя бы одного продукта
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-qa='product-name']"))
            )
        except:
            print("⚠️ Элементы продуктов не найдены на странице.")
            # для дебага можно вывести весь HTML страницы
            print(self.driver.page_source[:1000])  # первые 1000 символов
            return None

        # Скроллим страницу до конца, чтобы подгрузились все товары
        SCROLL_PAUSE_TIME = 2
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        products = []
        try:
            title_blocks = self.driver.find_elements(By.CSS_SELECTOR, "a[data-qa='product-name']")
            price_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span[data-qa='primary-price-main']")
            unit_blocks = self.driver.find_elements(By.CSS_SELECTOR, "span.p1yvm8ab_plp")

            for i, title_block in enumerate(title_blocks):
                try:
                    name = title_block.text.strip()
                    url = title_block.get_attribute("href")

                    price_text = price_blocks[i].text.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
                    price = Decimal(price_text)
                    unit = unit_blocks[i].text.strip() if i < len(unit_blocks) else None

                    products.append({"name": name, "price": price, "unit": unit, "url": url})
                    print(f"💰 Найден продукт: {name} — {price} {unit} — {url}")

                    if len(products) >= 15:
                        break
                except Exception as e:
                    print(f"❌ Ошибка при обработке одного продукта: {e}")
                    continue
        except Exception as e:
            print(f"❌ Ошибка при сборе блоков продуктов: {e}")
            return None

        if not products:
            print("⚠️ Продукты не найдены после обработки блоков.")
            return None

        # Можно посчитать среднюю цену, если нужно
        prices = [p["price"] for p in products]
        avg_price = sum(prices) / len(prices) if prices else None

        return {"products": products, "avg_price": avg_price}



# import asyncio

# from playwright.async_api import async_playwright
# import json
#
#
# async def get_price_from_product_page(page, product_url: str) -> str | None:
#     await page.goto(product_url, timeout=60000)
#     await page.wait_for_timeout(3000)
#
#     json_ld_tags = await page.query_selector_all('script[type="application/ld+json"]')
#     for tag in json_ld_tags:
#         try:
#             json_ld_text = await tag.inner_text()
#             data = json.loads(json_ld_text)
#
#             if isinstance(data, list):
#                 for entry in data:
#                     if "offers" in entry and "price" in entry["offers"]:
#                         return entry["offers"]["price"]
#             elif "offers" in data and "price" in data["offers"]:
#                 return data["offers"]["price"]
#         except json.JSONDecodeError:
#             continue
#
#     try:
#         price_el = await page.query_selector('[data-qa="primary-price-main"]')
#         if price_el:
#             price_text = await price_el.inner_text()
#             return price_text.replace('\xa0', '').strip()
#     except Exception as e:
#         print("Ошибка при парсинге HTML цены:", e)
#
#     return None
#
#
# async def search_lemanapro_products(query: str) -> list[dict]:
#     url = f"https://lemanapro.ru/search/?q={query.replace(' ', '%20')}&suggest=true"
#
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True, args=[
#             "--disable-blink-features=AutomationControlled"
#         ])
#         context = await browser.new_context(
#             locale="ru-RU",
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#                        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
#         )
#         page = await context.new_page()
#         await page.goto(url, timeout=60000)
#         await page.wait_for_selector('[data-qa="product-name"]', timeout=10000)
#
#         products = []
#         product_cards = await page.query_selector_all('[data-qa="product-name"]')
#         for card in product_cards:
#             name_span = await card.query_selector("span")
#             name = await name_span.inner_text() if name_span else "—"
#             link_href = await card.get_attribute("href")
#             full_url = f"https://lemanapro.ru{link_href}" if link_href else None
#
#             price = None
#             if full_url:
#                 product_page = await context.new_page()
#                 price = await get_price_from_product_page(product_page, full_url)
#                 await product_page.close()
#
#             products.append({
#                 "name": name.strip(),
#                 "price": price.strip() if price else None,
#                 "url": full_url,
#             })
#
#         await browser.close()
#         return products
#
#
# if __name__ == "__main__":
#     query = "перчатки хлопчатобумажные"
#     results = asyncio.run(search_lemanapro_products(query))
#     from pprint import pprint
#     pprint(results)

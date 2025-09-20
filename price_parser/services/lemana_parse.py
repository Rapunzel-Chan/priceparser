import time
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from decimal import Decimal

class LemanaProScraper:
    def __init__(self, headless=True):
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument("start-maximized")
        options.add_argument("window-size=1920,1080")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        self.base_url = "https://lemanapro.ru/search/?q="

    def close(self):
        self.driver.quit()

    def find_matching_products(self, product_name):
        query = ' '.join(product_name.lower().split()[:3])
        search_url = self.base_url + quote(query)
        self.driver.get(search_url)

        # Ждем, пока появятся карточки товаров
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.pr7cfcb_plp.largeCard'))
            )
        except:
            print("Товары не найдены или страница не загрузилась")
            return None

        products = []
        cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.pr7cfcb_plp.largeCard')[:10]

        for card in cards:
            try:
                a_tag = card.find_element(By.CSS_SELECTOR, 'div.c1gua8e6_plp a')
                name = a_tag.find_element(By.CSS_SELECTOR, 'span.product-card-name-link').text.strip()
                url = "https://lemanapro.ru" + a_tag.get_attribute('href')

                price_span = card.find_element(By.CSS_SELECTOR, 'div.p1otuot_plp span[data-qa="primary-price-main"]')
                price = Decimal(price_span.text.replace('\xa0','').replace(' ',''))

                unit = card.find_element(By.CSS_SELECTOR, 'div.p1otuot_plp span.p1yvm8ab_plp').text.strip()

                products.append({
                    'name': name,
                    'price': price,
                    'unit': unit,
                    'url': url
                })
            except:
                continue

        return products if products else None



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


import time
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from decimal import Decimal
from price_parser.utils.price_utils import filtered_unique_mean

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
        time.sleep(4)  # пауза, чтобы страница загрузилась

        products = []

        try:
            # Находим контейнеры с товарами
            title_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'div.c1gua8e6_plp')
            price_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'div.p1otuot_plp')

            for title_block, price_block in zip(title_blocks[:10], price_blocks[:10]):  # топ-10
                a_tag = title_block.find_element(By.CSS_SELECTOR, 'a[data-qa="product-name"]')
                name_span = a_tag.find_element(By.CSS_SELECTOR, 'span.product-card-name-link')
                name = name_span.text.strip()
                url = "https://lemanapro.ru" + a_tag.get_attribute('href')

                price_main = price_block.find_element(By.CSS_SELECTOR, 'span[data-qa="primary-price-main"]').text.strip()
                price = Decimal(price_main.replace('\xa0', '').replace(' ', ''))

                unit = price_block.find_element(By.CSS_SELECTOR, 'span.p1yvm8ab_plp').text.strip()

                products.append({
                    'name': name,
                    'price': price,
                    'unit': unit,
                    'url': url,
                })

        except Exception as e:
            print(f"Ошибка при парсинге: {e}")

        if not products:
            return None

        # Расчёт средней цены с trim_pct
        prices = [p['price'] for p in products]
        avg_price = filtered_unique_mean(prices, trim_pct=0.3)

        return {
            'products': products,
            'avg_price': avg_price
        }

if __name__ == "__main__":
    scraper = LemanaProScraper(headless=False)
    try:
        result = scraper.find_matching_products("перчатки хлопчатобумажные")
        print(result)
    finally:
        scraper.close()

# import time

# from urllib.parse import quote
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
#
# class LemanaProScraper:
#     def __init__(self, headless=True):
#         options = Options()
#         if headless:
#             options.add_argument('--headless')
#         options.add_argument('--disable-blink-features=AutomationControlled')
#         options.add_argument('--no-sandbox')
#         options.add_argument('--disable-gpu')
#         options.add_argument("start-maximized")
#         options.add_argument("window-size=1920,1080")
#         options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                              "AppleWebKit/537.36 (KHTML, like Gecko) "
#                              "Chrome/114.0.0.0 Safari/537.36")
#         self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#         self.base_url = "https://lemanapro.ru/search/?q="
#
#     def close(self):
#         self.driver.quit()
#
#     def find_matching_products(self, product_name):
#         query = ' '.join(product_name.lower().split()[:3])
#         search_url = self.base_url + quote(query)
#         self.driver.get(search_url)
#         time.sleep(4)  # увеличить паузу, чтобы страница загрузилась
#
#         products = []
#
#         try:
#             # Ищем контейнеры с товарами (каждый товар - два соседних блока)
#             product_title_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'div.c1gua8e6_plp')
#             price_blocks = self.driver.find_elements(By.CSS_SELECTOR, 'div.p1otuot_plp')
#
#             for title_block, price_block in zip(product_title_blocks, price_blocks):
#                 # Название и ссылка
#                 a_tag = title_block.find_element(By.CSS_SELECTOR, 'a[data-qa="product-name"]')
#                 name_span = a_tag.find_element(By.CSS_SELECTOR, 'span.product-card-name-link')
#                 name = name_span.text.strip()
#                 url = "https://lemanapro.ru" + a_tag.get_attribute('href')
#
#                 # Цена и единица измерения
#                 price_main = price_block.find_element(By.CSS_SELECTOR, 'span[data-qa="primary-price-main"]').text.strip()
#                 price = float(price_main.replace('\xa0', '').replace(' ', ''))
#                 unit = price_block.find_element(By.CSS_SELECTOR, 'span.p1yvm8ab_plp').text.strip()
#
#                 products.append({
#                     'name': name,
#                     'price': price,
#                     'unit': unit,
#                     'url': url,
#                 })
#
#         except Exception as e:
#             print(f"Ошибка при парсинге: {e}")
#
#         if not products:
#             return None
#         return products
#
#
# if __name__ == "__main__":
#     scraper = LemanaProScraper(headless=False)
#     try:
#         results = scraper.find_matching_products("перчатки хлопчатобумажные")
#         print(results)
#     finally:
#         scraper.close()

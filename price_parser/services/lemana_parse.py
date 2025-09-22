import json
from decimal import Decimal
from urllib.parse import quote
from playwright.async_api import async_playwright
from price_parser.utils.price_utils import filtered_unique_mean

async def search_lemanapro_products(product_name: str, page=None):
    """
    Парсит один товар.
    Если передан page, будет использовать его вместо создания нового.
    Возвращает: {"products": [{"name":..., "price":..., "unit":..., "url":...}], "avg_price": ...}
    """
    own_browser = False
    if page is None:
        own_browser = True
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

    try:
        query = quote(product_name)
        url = f"https://lemanapro.ru/search/?q={query}"
        await page.goto(url, timeout=60000)
        await page.wait_for_selector('[data-qa="product-name"]', timeout=10000)

        product_cards = await page.query_selector_all('[data-qa="product-name"]')
        products = []

        for card in product_cards[:10]:  # только первые 10
            name = await (await card.query_selector("span")).inner_text()
            href = await card.get_attribute("href")
            full_url = f"https://lemanapro.ru{href}" if href else None

            # Переходим на страницу товара для точной цены
            price = None
            unit = None
            if full_url:
                if own_browser:
                    new_page = await context.new_page()
                else:
                    new_page = page  # используем переданную страницу для batch
                await new_page.goto(full_url, timeout=60000)
                await new_page.wait_for_selector('[data-qa="price-view"]', timeout=10000)
                try:
                    price_el = await new_page.query_selector('[data-qa="price-view"] span')
                    if price_el:
                        price_text = await price_el.inner_text()
                        price = Decimal(price_text.replace("₽", "").replace(",", ".").strip())
                        unit = "шт."
                except Exception:
                    pass
                if own_browser:
                    await new_page.close()

            if price is not None:
                products.append({
                    "name": name.strip(),
                    "price": price,
                    "unit": unit,
                    "url": full_url
                })

        if not products:
            return None

        avg_price = filtered_unique_mean([p["price"] for p in products], trim_pct=0.3)
        return {"products": products, "avg_price": avg_price}
    finally:
        if own_browser:
            await browser.close()
            await playwright.stop()


async def async_search_multiple_products(product_names: list[str]):
    """
    Парсинг нескольких продуктов за один браузер (batch).
    """
    results_dict = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for name in product_names:
            results = await search_lemanapro_products(name, page=page)
            results_dict[name] = results

        await browser.close()
    return results_dict



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

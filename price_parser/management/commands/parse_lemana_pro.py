# import asyncio
# from django.core.management.base import BaseCommand
# from catalog.models import Product, ParsedProduct
# from catalog.services.lemana_parse import search_lemanapro_products
# from django.utils.timezone import now
# from datetime import timedelta
#
#
# def is_price_valid(price):
#     try:
#         return 100 <= float(price) <= 10000
#     except:
#         return False
#
#
# def filter_prices(prices: list[float]) -> list[float]:
#     if not prices:
#         return []
#
#     unique_prices = sorted(set(prices))
#     n = len(unique_prices)
#     if n < 10:
#         # Мало данных — возвращаем все уникальные
#         return unique_prices
#
#     lower_idx = int(n * 0.05)
#     upper_idx = int(n * 0.95)
#     return unique_prices[lower_idx:upper_idx]
#
#
# def average_price(prices: list[float]) -> float | None:
#     filtered = filter_prices(prices)
#     if not filtered:
#         return None
#     return sum(filtered) / len(filtered)
#
#
# class Command(BaseCommand):
#     help = "Парсинг товаров с lemanapro.ru"
#
#     def add_arguments(self, parser):
#         parser.add_argument('--product', type=str, help='Название одного товара')
#         parser.add_argument('--shortlist', action='store_true', help='Парсить только основные товары (is_main=True)')
#
#     def handle(self, *args, **options):
#         loop = asyncio.get_event_loop()
#
#         if options['product']:
#             products = Product.objects.filter(name=options['product'])
#         elif options['shortlist']:
#             products = Product.objects.filter(is_main=True)
#         else:
#             products = Product.objects.all()
#
#         self.stdout.write(f'🔍 Найдено {products.count()} товаров для обработки')
#
#         # Удаляем устаревшие цены (старше 1 дня)
#         cutoff = now() - timedelta(days=1)
#         deleted_count, _ = ParsedProduct.objects.filter(fetched_at__lt=cutoff).delete()
#         self.stdout.write(f'🗑 Удалено устаревших цен: {deleted_count}')
#
#         today = now().date()
#
#         for product in products:
#             query = ' '.join(product.name.split()[:4])
#             self.stdout.write(f'📦 Парсим: {product.name}')
#             try:
#                 results = loop.run_until_complete(search_lemanapro_products(query))
#             except Exception as e:
#                 self.stdout.write(self.style.ERROR(f'❌ Ошибка при запросе: {e}'))
#                 continue
#
#             raw_prices = []
#             url_price_map = {}
#
#             for item in results[:10]:
#                 price_str = item.get('price')
#                 if is_price_valid(price_str):
#                     price_float = float(price_str)
#                     raw_prices.append(price_float)
#                     url_price_map[item['url']] = (price_float, item['name'])
#
#             filtered_prices = filter_prices(raw_prices)
#             avg_price = average_price(raw_prices)
#
#             if avg_price is None:
#                 self.stdout.write(self.style.WARNING('⚠️ Нет подходящих цен после фильтрации'))
#                 continue
#
#             # Сохраняем среднюю цену в продукте
#             product.avg_price_lemanapro = round(avg_price, 2)
#             product.save(update_fields=['avg_price_lemanapro'])
#
#             count_saved = 0
#             for url, (price_float, name) in url_price_map.items():
#                 parsed_qs = ParsedProduct.objects.filter(url=url, fetched_at__date=today)
#
#                 if parsed_qs.exists():
#                     parsed_product = parsed_qs.first()
#                     if parsed_product.price != price_float:
#                         parsed_product.price = price_float
#                         parsed_product.fetched_at = now()
#                         parsed_product.save()
#                         count_saved += 1
#                 else:
#                     ParsedProduct.objects.create(
#                         url=url,
#                         name=name,
#                         price=price_float,
#                         source='lemanapro',
#                         fetched_at=now()
#                     )
#                     count_saved += 1
#
#             self.stdout.write(self.style.SUCCESS(f'✅ Обновлено/создано цен: {count_saved}'))
#             self.stdout.write(f'Найденные цены: {", ".join(map(str, filtered_prices))}')
#             self.stdout.write(f'Средняя цена: {avg_price:.2f}')
#
from django.core.management.base import BaseCommand
from price_parser.models import Product, ParsedProduct
from price_parser.utils.price_utils import extract_unit_and_pack
from django.utils.timezone import now
from datetime import timedelta
from decimal import Decimal
from price_parser.utils.price_utils import filtered_unique_mean
import asyncio
from price_parser.services.lemana_parse import search_lemanapro_products


class Command(BaseCommand):
    help = "Парсинг товаров с lemanapro.ru"

    def add_arguments(self, parser):
        parser.add_argument('--product', type=str, help='Название одного товара')
        parser.add_argument('--shortlist', action='store_true', help='Парсить только основные товары (is_main=True)')

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()

        if options['product']:
            products = Product.objects.filter(name=options['product'])
        elif options['shortlist']:
            products = Product.objects.filter(is_main=True)
        else:
            products = Product.objects.all()

        self.stdout.write(f'🔍 Найдено {products.count()} товаров для обработки')

        # Удаляем устаревшие ParsedProduct
        cutoff = now() - timedelta(days=1)
        ParsedProduct.objects.filter(fetched_at__lt=cutoff).delete()

        for product in products:
            query = ' '.join(product.name.split()[:4])
            self.stdout.write(f'📦 Парсим: {product.name}')

            try:
                results = loop.run_until_complete(search_lemanapro_products(query))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Ошибка при запросе: {e}'))
                continue

            raw_prices = []
            url_price_map = {}

            for item in results[:10]:
                price_float = float(item['price'])
                raw_prices.append(price_float)
                url_price_map[item['url']] = (price_float, item['name'])

            avg_price_pack = filtered_unique_mean(raw_prices)
            if avg_price_pack is None:
                self.stdout.write(self.style.WARNING('⚠️ Нет подходящих цен после фильтрации'))
                continue

            # Извлекаем unit и pack_size
            unit, pack_size = extract_unit_and_pack(product.name)
            price_per_unit = avg_price_pack / pack_size if pack_size else avg_price_pack

            # Сохраняем данные
            product.unit = unit
            product.pack_size = pack_size
            product.avg_price_lemanapro = price_per_unit.quantize(Decimal('0.01'))
            product.save(update_fields=['unit', 'pack_size', 'avg_price_lemanapro'])

            self.stdout.write(self.style.SUCCESS(f'✅ {product.name}: {price_per_unit:.2f} {unit}'))

            # Сохраняем ParsedProduct
            for url, (price_float, name) in url_price_map.items():
                ParsedProduct.objects.update_or_create(
                    url=url,
                    fetched_at__date=now().date(),
                    defaults={'name': name, 'price': price_float, 'source': 'lemanapro', 'fetched_at': now()}
                )

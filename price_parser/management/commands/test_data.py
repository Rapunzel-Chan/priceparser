# from django.core.management.base import BaseCommand

# from price_parser.models import ParsedProduct, Product

# class Command(BaseCommand):
#     help = "Загрузить тестовые данные для товара М300 Пескобетон"
#
#     def handle(self, *args, **options):
#         # Создаем товар
#         product, created = Product.objects.get_or_create(
#             name="М300 Пескобетон ГОСТ 40кг 49шт/под",
#             defaults={
#                 "price": 3500,  # например
#                 "category_id": 20,  # замени на существующий ID категории
#                 "source": "manual",
#             }
#         )
#         if created:
#             self.stdout.write(self.style.SUCCESS(f"Товар '{product.name}' создан"))
#
#         # Создаем несколько parsed записей с разными ценами
#         parsed_prices = [3400, 3600, 3550]
#
#         for price in parsed_prices:
#             pp = ParsedProduct.objects.create(
#                 name=product.name,
#                 price=price,
#                 url="https://example.com/product",
#                 source="lemanapro"
#             )
#             self.stdout.write(self.style.SUCCESS(f"Добавлена запись ParsedProduct с ценой {price}"))
#
#         self.stdout.write(self.style.SUCCESS("Тестовые данные загружены"))

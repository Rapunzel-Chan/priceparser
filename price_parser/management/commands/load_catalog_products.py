from django.core.management.base import BaseCommand
from catalog.services.parser_exl import ProductParser
from catalog.models import Category, Product
from django.core.management.base import BaseCommand

import pandas as pd
from django.core.management.base import BaseCommand
from catalog.models import Category, Product


class Command(BaseCommand):
    help = "Импорт товаров из Excel файла в БД"

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Путь к Excel файлу с каталогом'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        df = pd.read_excel(file_path, header=None)

        category = None
        created_products = 0

        for idx, row in df.iterrows():
            # Пример: категория начинается с номера и точки "01. Сухие смеси"
            first_cell = str(row[0]) if not pd.isna(row[0]) else ''

            # Проверяем, является ли строка категорией
            if first_cell and pd.notna(first_cell) and first_cell.strip() != '':
                if first_cell.strip()[0:2].isdigit() and first_cell.strip()[2] == '.':
                    # Извлекаем название категории после номера и точки
                    category_name = first_cell.strip()[3:].strip()
                    if category_name:
                        category = category_name
                    else:
                        category = None
                    continue

            # Если категории ещё нет, пропускаем строки (товары без категории не добавляем)
            if not category:
                continue

            # Товары начинаются с 5-го столбца (индекс 4)
            product_name = row[4] if len(row) > 4 else None
            unit = row[5] if len(row) > 5 else None

            if pd.isna(product_name) or not str(product_name).strip():
                # Пропускаем пустые строки или отсутствующие товары
                continue

            # Получаем или создаём категорию
            category_obj, _ = Category.objects.get_or_create(name=category)

            # Создаём продукт, цена пока пустая (None)
            product, created = Product.objects.get_or_create(
                name=product_name.strip(),
                category=category_obj,
                defaults={
                    'price': None,
                    'source': 'leroy_merlen',
                }
            )

            if created:
                # Обновляем единицу измерения, если есть поле unit у модели,
                # если нет, пропусти этот шаг или добавь поле в модель
                # Пример:
                # product.unit = unit
                # product.save()
                created_products += 1

        self.stdout.write(f"✅ Успешно импортировано {created_products} новых товаров.")


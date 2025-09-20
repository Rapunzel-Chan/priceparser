
from django.core.management.base import BaseCommand
from price_parser.models import Product, Category
import csv
import os

class Command(BaseCommand):
    help = "Загрузка товаров из CSV-файла с флагом is_main=True"

    def handle(self, *args, **kwargs):
        path = os.path.join('shortlist.csv')
        with open(path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            added = 0
            for row in reader:
                name = row['name'].strip()
                category_name = row['category'].strip()

                category, _ = Category.objects.get_or_create(name=category_name)
                Product.objects.update_or_create(
                    name=name,
                    category=category,
                    defaults={'is_main': True}
                )
                added += 1
        self.stdout.write(self.style.SUCCESS(f'✅ Загружено {added} товаров из шортлиста'))

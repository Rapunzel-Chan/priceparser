import openpyxl
from django.core.management.base import BaseCommand
from openpyxl.utils import get_column_letter

from price_parser.models import ParsedProduct


class Command(BaseCommand):
    help = "Экспорт всех обработанных товаров с ценами в Excel"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", type=str, default="parsed_products.xlsx", help="Путь к файлу для сохранения Excel"
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        products = ParsedProduct.objects.all().order_by("name")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Parsed Products"

        headers = ["Название", "Цена", "URL", "Источник"]
        ws.append(headers)

        for product in products:
            ws.append(
                [
                    product.name,
                    product.price,
                    product.url,
                    product.source,
                ]
            )

        # Автоширина колонок
        for col_num, column_title in enumerate(headers, 1):
            column_letter = get_column_letter(col_num)
            ws.column_dimensions[column_letter].width = max(len(column_title) + 2, 15)

        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(f'✅ Экспортировано {products.count()} товаров в "{output_path}"'))

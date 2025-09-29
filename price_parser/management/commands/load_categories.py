from django.core.management.base import BaseCommand

from price_parser.models import Category


class Command(BaseCommand):
    help = "Загрузить категории в БД"

    def handle(self, *args, **kwargs):
        categories = ["Расходные материалы", "Сухие смеси", "Прочее", "Инструмент", "Шортлист"]
        for name in categories:
            Category.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Категории успешно загружены"))

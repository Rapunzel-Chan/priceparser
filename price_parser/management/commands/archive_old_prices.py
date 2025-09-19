from django.core.management.base import BaseCommand
from catalog.models import ParsedProduct, ParsedProductArchive
from django.utils.timezone import now
from datetime import timedelta

class Command(BaseCommand):
    help = "Архивирует старые цены из ParsedProduct в ParsedProductArchive"

    def handle(self, *args, **options):
        cutoff = now() - timedelta(days=1)
        old_prices = ParsedProduct.objects.filter(fetched_at__lt=cutoff)
        count = old_prices.count()
        if count == 0:
            self.stdout.write("❗ Старых цен для архивирования не найдено.")
            return

        for old in old_prices:
            ParsedProductArchive.objects.create(
                name=old.name,
                price=old.price,
                unit=old.unit,
                url=old.url,
                source=old.source,
                fetched_at=old.fetched_at
            )
        old_prices.delete()
        self.stdout.write(f"✅ Заархивировано и удалено {count} старых цен.")

from django.core.management.base import BaseCommand
from catalog.models import Product
from catalog.services.lemana_pro_parser import LemanaProScraper


class Command(BaseCommand):
    help = 'Сопоставляет товары с ценами с LemanaPro'

    def handle(self, *args, **kwargs):
        scraper = LemanaProScraper(headless=True)

        try:
            products = Product.objects.all()

            for product in products:
                product_name = product.name
                matches = scraper.find_matching_products(product_name)

                if not matches:
                    self.stdout.write(f"⚠️ {product_name} — совпадений не найдено")
                    continue

                best_match = matches[0]  # Можно улучшить логику выбора
                self.stdout.write(
                    f"✅ {product_name} — {best_match['price']} {best_match['unit']} ({best_match['url']})"
                )

        finally:
            scraper.close()
from django.core.management.base import BaseCommand
from catalog.models import Product
from catalog.services.lemana_pro_parser import LemanaProScraper
from decimal import Decimal


class Command(BaseCommand):
    help = 'Обновляет цены из Lemanapro по названию товара'

    def handle(self, *args, **kwargs):
        scraper = LemanaProScraper(headless=False)
        updated = 0
        skipped = 0

        try:
            products = Product.objects.all()
            for product in products:
                matches = scraper.find_matching_products(product.name)

                if matches:
                    avg_price = sum([m["price"] for m in matches]) / len(matches)
                    first_unit = matches[0]["unit"]

                    product.price = Decimal(str(round(avg_price, 2)))
                    product.save(update_fields=["price"])

                    self.stdout.write(
                        f"✅ {product.name} — {avg_price} {first_unit} ({len(matches)} совп.)"
                    )
                    updated += 1
                else:
                    self.stdout.write(f"⚠️  {product.name} — совпадений не найдено")
                    skipped += 1
        finally:
            scraper.close()

        self.stdout.write(self.style.SUCCESS(f"\nИтог: обновлено: {updated}, пропущено: {skipped}"))

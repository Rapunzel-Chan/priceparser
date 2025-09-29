from django.db import models

# Create your models here.

from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json
from django.db import models
from django.db.models import Avg
from django.utils import timezone

from config import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# class SubCategory(models.Model):
#     """Подкатегория (Шпаклёвки, Грунтовки и т.д.)"""
#     name = models.CharField(max_length=100, unique=True)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
#
#     def __str__(self):
#         return f"{self.category.name} / {self.name}"


class Product(models.Model):
    SOURCE_CHOICES = [
        # ('ozon', 'Ozon'),
        # ('yandex', 'Yandex'),
        ('lemanapro', 'LemanaPro'),
        # при необходимости добавь другие источники здесь
    ]

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='lemanapro')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    # subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    parsed = models.BooleanField(default=False)
    is_main = models.BooleanField(default=False)
    avg_price_lemanapro = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                              verbose_name="Средняя цена Lemanapro (за единицу)")
    unit = models.CharField(max_length=20, null=True, blank=True)
    pack_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    popularity = models.IntegerField(default=0)
    parsing_done = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='products'
    )

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return f"{self.name} ({self.source})"

    # def average_price(self):
    #     prices = self.price.filter(price__gt=100, price__lt=10000)  # фильтр по цене
    #     return prices.aggregate(Avg('price'))['price__avg']
    def average_price(self):
        return self.avg_price_lemanapro

class ParsedProduct(models.Model):
    product = models.ForeignKey(
        "Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="parsed_products"
    )
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    pack_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)
    source = models.CharField(max_length=100, default='lemanapro')
    fetched_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='parsed_products'
    )
    parser = models.ForeignKey(
        "ParserSchedule", null=True, blank=True, on_delete=models.SET_NULL, related_name="parsed_products"
    )
    class Meta:
        indexes = [models.Index(fields=['name'])]

class ParsedProductArchive(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='parsed_products_archive', default=1)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50, blank=True, null=True)
    pack_size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    url = models.URLField(blank=True, null=True)
    source = models.CharField(max_length=50, default='lemanapro')
    fetched_at = models.DateTimeField(default=timezone.now)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='parsed_products_archieve'
    )
    class Meta:
        indexes = [models.Index(fields=['name'])]


from django.db import models
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json
from config import settings

class ParserSchedule(models.Model):
    PLATFORM_CHOICES = [
        ('Lemana Pro', 'Lemana Pro'),
        ('Ozon', 'Ozon'),
        ('Yandex', 'Yandex'),
    ]

    platform = models.CharField(
        max_length=255,
        verbose_name="Площадка",
        choices=PLATFORM_CHOICES,
        default='Lemana Pro'
    )
    name = models.CharField(max_length=255, verbose_name="Название парсера")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_run = models.DateTimeField(null=True, blank=True)
    manual = models.BooleanField(default=False)
    interval = models.CharField(max_length=50, default="6h")
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField('Product', blank=True, related_name='parsers')



    def _parse_interval(self):
        """
        Возвращает (every:int, period:str) для django_celery_beat IntervalSchedule
        INPUT examples: '6h', '30m', '1d', '15' (тогда считаем минуты)
        """
        s = (self.interval or "").strip().lower()
        if not s:
            return 6, "hours"

        import re
        m = re.match(r'(\d+)\s*([smhd])?', s)
        if not m:
            # fallback: если просто число — минуты
            try:
                return int(s), "minutes"
            except Exception:
                return 6, "hours"

        val = int(m.group(1))
        unit = m.group(2) or "m"
        mapping = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        return val, mapping.get(unit, "minutes")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Создаём/обновляем PeriodicTask для всех продуктов парсера
        # product_ids = list(self.products.values_list('id', flat=True))
        if not self.manual and self.is_active and self.products.exists():
            every, period = self._parse_interval()
            schedule, _ = IntervalSchedule.objects.get_or_create(every=every, period=period)
            PeriodicTask.objects.update_or_create(
                name=f"parse_{self.pk}",
                defaults={
                    "interval": schedule,
                    "task": "price_parser.tasks.parse_parser_products",
                    "args": json.dumps([self.pk]),
                    "enabled": True
                },
            )
        else:
            # если ручной или выключен или нет продуктов — удалим периодическую таску
            PeriodicTask.objects.filter(name=f"parse_{self.pk}").delete()

    def __str__(self):
        return f"{self.name} ({self.platform})"


class ProductPriceHistory(models.Model):
    """История изменения средней цены товара"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    date = models.DateField()
    avg_price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.product.name} - {self.date}: {self.avg_price_per_unit}"

class Contacts(models.Model):
    country = models.CharField("Страна", max_length=100)
    inn = models.CharField("ИНН", max_length=20)
    address = models.CharField("Адрес", max_length=255)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контактные данные"

    def __str__(self):
        return f"{self.country}, {self.address}"

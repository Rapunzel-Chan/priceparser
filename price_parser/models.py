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
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='leroy_merlen')
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
    url = models.URLField(max_length=500, null=True, blank=True)
    source = models.CharField(max_length=100, default='lemanapro')
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

class ParsedProductArchive(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='parsed_products_archive', default=1)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50, blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    source = models.CharField(max_length=50, default='lemanapro')
    fetched_at = models.DateTimeField(auto_now_add=True)

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_run = models.DateTimeField(null=True, blank=True)
    manual = models.BooleanField(default=False)
    interval = models.CharField(max_length=50, default="6h")
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField('Product', blank=True, related_name='parsers')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Создаём/обновляем PeriodicTask для всех продуктов парсера
        product_ids = list(self.products.values_list('id', flat=True))
        if product_ids:
            schedule, _ = IntervalSchedule.objects.get_or_create(every=self.interval, period='minutes')
            PeriodicTask.objects.update_or_create(
                name=f"parse_{self.pk}",
                defaults={
                    'interval': schedule,
                    'task': 'price_parser.tasks.parse_parser_products',  # таск пройдётся по всем продуктам
                    'args': json.dumps([self.pk]),  # передаем ID парсера
                }
            )

    def __str__(self):
        return f"{self.name} ({self.platform})"


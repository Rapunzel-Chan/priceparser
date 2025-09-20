from django.db import models

# Create your models here.


from django.db import models
from django.db.models import Avg
from django.utils import timezone


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
        ('leroy_merlen', 'Leroy Merlen'),
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
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)
    source = models.CharField(max_length=100)  # Например: 'lemanapro'
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

class ParsedProductArchive(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField(max_length=500, null=True, blank=True)
    source = models.CharField(max_length=100)
    fetched_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['name'])]

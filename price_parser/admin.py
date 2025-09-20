from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Product, ParsedProduct, ParsedProductArchive

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'avg_price_lemanapro', 'is_main', 'unit', 'pack_size', 'popularity')
    list_filter = ('category', 'is_main')
    search_fields = ('name',)

@admin.register(ParsedProduct)
class ParsedProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'unit', 'source', 'fetched_at')

@admin.register(ParsedProductArchive)
class ParsedProductArchiveAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'unit', 'source', 'fetched_at')

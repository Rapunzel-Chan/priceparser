from django.urls import path
from django.views.decorators.cache import cache_page

from . import views
from .views import ProductSelectView, ProductResultView, ExportExcelView
from price_parser.apps import PriceParserConfig
from price_parser.views import AddProductsView
# from catalog.views import (CategoryListView, ContactsView, ProductCategoryListView, ProductCreateView,
#                            ProductDeleteView, ProductDetailView, ProductListView, ProductUpdateView,
#                            UnpublishProductView)

app_name = PriceParserConfig.name

urlpatterns = [
    path('products/', ProductSelectView.as_view(), name='select_products'),  # Главная: выбор товаров
    path('results/', ProductResultView.as_view(), name='show_selected_products'),
    # # path('excel/', ExportExcelView.as_view(), name='export_excel'),
    path('add-products/', AddProductsView.as_view(), name='add_or_select_products'),
    # path('add_products/', views.AddProductsView.as_view(), name='add_products'),  # Можно заменить на новую страницу
    path('products_by_category/', views.ProductsByCategoryView.as_view(), name='get_products_by_category'),
    # path('results/', views.ProductResultView.as_view(), name='product_results'),
    path('export_excel/', views.ExportExcelView.as_view(), name='export_excel'),
    path('parse_product/', views.ParseProductView.as_view(), name='parse_product'),
]

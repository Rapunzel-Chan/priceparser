from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from . import views
from .views import ProductSelectView, ProductDetailView, IndexView
from price_parser.apps import PriceParserConfig
# from price_parser.views import AddProductsView
# # from catalog.views import (CategoryListView, ContactsView, ProductCategoryListView, ProductCreateView,
# #                            ProductDeleteView, ProductDetailView, ProductListView, ProductUpdateView,
# #                            UnpublishProductView)

app_name = PriceParserConfig.name

urlpatterns = [
#     # path('products/', ProductSelectView.as_view(), name='select_products'),  # Главная: выбор товаров
#     # path('results/', ProductResultView.as_view(), name='show_selected_products'),
#     # # # path('excel/', ExportExcelView.as_view(), name='export_excel'),
#     # path('add-products/', AddProductsView.as_view(), name='add_or_select_products'),
#     # # path('add_products/', views.AddProductsView.as_view(), name='add_products'),  # Можно заменить на новую страницу
#     # path('products_by_category/', views.ProductsByCategoryView.as_view(), name='get_products_by_category'),
#     # # path('results/', views.ProductResultView.as_view(), name='product_results'),
#     # path('export_excel/', views.ExportExcelView.as_view(), name='export_excel'),
#     # path('parse_product/', views.ParseProductView.as_view(), name='parse_product'),
#     # # path('subcategories/', views.SubCategoriesByCategoryView.as_view(), name='get_subcategories')
#     # path('product/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
#
    path('', views.IndexView.as_view(), name='index1'),
    # --- Категории ---
    path('categories/', views.CategoryListView.as_view(), name='categories'),  # список категорий

    # --- Выбор товаров (новая страница) ---
    path('selected/', views.ProductSelectView.as_view(), name='add_or_select_products'),
    path('selected/action/', views.ProductSelectActionView.as_view(), name='selected_action'),
    path('parsing_status/', views.ParsingStatusView.as_view(), name='parsing_status'),
    # --- Добавление новых товаров ---
    # path('add/', views.AddProductsView.as_view(), name='add_products'),

    # --- AJAX: товары по категории ---
    # path('products_by_category/', views.ProductsByCategoryView.as_view(), name='products_by_category'),

    # --- AJAX: парсинг одного товара ---
    # path('parse_product/', views.ParseProductView.as_view(), name='parse_product'),

    # --- AJAX: парсинг всех выбранных товаров ---
    # path('parse_selected/', views.ParseSelectedProductsView.as_view(), name='parse_selected'),

    # --- Экспорт выбранных в Excel ---
    path('export_excel/', views.ExportSummaryExcelView.as_view(), name='export_summary_excel'),
    path('export_excel_details/', views.ExportDetailedExcelView.as_view(), name='export_detailed_excel'),
    path('results/', views.ResultsView.as_view(), name='show_selected_products'),

    # --- Детали конкретного товара ---
    path('products/', views.ProductListView.as_view(), name='products_list'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('parsers/', views.ParsersListView.as_view(), name='parsers'),
    path('parsers/add/', views.AddParserView.as_view(), name='add_parser'),
    path('parsers/<int:pk>/select-products/', views.ParserSelectProductsView.as_view(), name='parser_select_products'),

    path('parsers/<int:pk>/edit/', views.EditParserView.as_view(), name='edit_parser'),
    path('parsers/<int:pk>/run/', views.RunParserNowView.as_view(), name='run_parser_now'),
    # path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('contacts/', TemplateView.as_view(template_name='contacts.html'), name='contacts'),
    # Reports
    path("reports/", views.ReportsView.as_view(), name="reports"),
    # path("contacts/", ContactsView.as_view(), name="contacts"),
    # --- СТАРЫЙ способ: вывод результатов (если нужен) ---
    # path('results/', views.ProductResultView.as_view(), name='show_selected_products'),
]

# urlpatterns = [
#     path('', views.ProductSelectView.as_view(), name='select_products'),
#     path('results/', views.ProductResultView.as_view(), name='show_selected_products'),
#     path('add-products/', views.AddProductsView.as_view(), name='add_or_select_products'),
#     path('products_by_category/', views.ProductsByCategoryView.as_view(), name='get_products_by_category'),
#     path('export_excel/', views.ExportExcelView.as_view(), name='export_excel'),
#     path('parse_product/', views.ParseProductView.as_view(), name='parse_product'),
#     path('parse_selected/', views.ParseSelectedProductsView.as_view(), name='parse_selected_products'),
#     path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
# ]
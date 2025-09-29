from django.urls import path

from price_parser.apps import PriceParserConfig

from . import views

app_name = PriceParserConfig.name

urlpatterns = [
    path("", views.IndexView.as_view(), name="index1"),
    path("categories/", views.CategoryListView.as_view(), name="categories"),
    path("selected/", views.ProductSelectView.as_view(), name="add_or_select_products"),
    path("selected/action/", views.ProductSelectActionView.as_view(), name="selected_action"),
    path("parsing_status/", views.ParsingStatusView.as_view(), name="parsing_status"),
    path("export_excel/", views.ExportSummaryExcelView.as_view(), name="export_summary_excel"),
    path("export_excel_details/", views.ExportDetailedExcelView.as_view(), name="export_detailed_excel"),
    path("results/", views.ResultsView.as_view(), name="show_selected_products"),
    path("products/", views.ProductListView.as_view(), name="products_list"),
    path("product/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("parsers/", views.ParsersListView.as_view(), name="parsers"),
    path("parsers/add/", views.AddParserView.as_view(), name="add_parser"),
    path("parsers/<int:pk>/select-products/", views.ParserSelectProductsView.as_view(), name="parser_select_products"),
    path("parsers/<int:pk>/edit/", views.EditParserView.as_view(), name="edit_parser"),
    path("parsers/<int:pk>/run/", views.RunParserNowView.as_view(), name="run_parser_now"),
    path("parsers/<int:pk>/delete/", views.DeleteParserView.as_view(), name="delete_parser"),
    path("reports/", views.ReportsView.as_view(), name="reports"),
    path("contacts/", views.ContactsView.as_view(), name="contacts"),
]

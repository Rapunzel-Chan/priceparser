from django.views import View
from django.views.generic import TemplateView, DetailView, ListView
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from decimal import Decimal
import json
import openpyxl

from .models import Product, Category, ParsedProduct
from .utils.price_utils import filtered_unique_mean, extract_unit_and_pack, clean_product_name
from .services.lemana_pro_parser import LemanaProScraper



# ============================
# Категории (список)
# ============================
class CategoryListView(ListView):
    model = Category
    template_name = 'categories.html'
    context_object_name = 'categories'


# ============================
# Выбор товаров + фильтр
# ============================

class ProductSelectView(TemplateView):
    template_name = 'add_or_select_products.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['q'] = self.request.GET.get('q', '')
        context['shortlist'] = self.request.GET.get('shortlist') == '1'

        queryset = Product.objects.all()
        if context['q']:
            queryset = queryset.filter(name__icontains=context['q'])
        if context['shortlist']:
            queryset = queryset.filter(is_main=True)

        context['products'] = queryset.order_by('name')
        return context


# ============================
# Парсинг одного товара через AJAX
# ============================

class ParseProductView(View):
    def post(self, request):
        data = json.loads(request.body)
        product_name = data.get('name')
        if not product_name:
            return JsonResponse({'error': 'Нет названия'}, status=400)

        scraper = LemanaProScraper(headless=True)
        try:
            results = scraper.find_matching_products(product_name)
        finally:
            scraper.close()

        if not results:
            return JsonResponse({'error': 'Товар не найден'}, status=404)

        # Берем среднее первых 10 позиций
        top10 = results[:10]
        prices = [Decimal(str(p['price'])) for p in top10]
        avg_price = filtered_unique_mean(prices)

        return JsonResponse({'avg_price_pack': float(avg_price) if avg_price else 0})


# ============================
# Парсинг всех выбранных
# ============================

class ParseSelectedProductsView(View):
    def post(self, request):
        ids = request.POST.getlist('ids[]')
        products = Product.objects.filter(id__in=ids)
        response = []

        scraper = LemanaProScraper(headless=True)
        try:
            for product in products:
                results = scraper.find_matching_products(product.name)
                if not results:
                    continue
                top10 = results[:10]
                prices = [Decimal(str(p['price'])) for p in top10]
                avg_price = filtered_unique_mean(prices)

                product.avg_price_lemanapro = avg_price if avg_price else 0
                product.save()

                response.append({'id': product.id, 'avg_price': float(avg_price) if avg_price else 0})
        finally:
            scraper.close()

        return JsonResponse({'updated': response})


# ============================
# Добавление товаров
# ============================

class AddProductsView(View):
    def get(self, request):
        categories = Category.objects.all()
        return render(request, 'add_products.html', {'categories': categories})

    def post(self, request):
        category_id = request.POST.get('category_id')
        product_names = request.POST.getlist('product_names[]')
        category = Category.objects.get(id=category_id)

        for name in product_names:
            if name.strip():
                Product.objects.get_or_create(
                    name=name.strip(),
                    category=category,
                    source='leroy_merlen'
                )
        return redirect('price_parser:select_products')


# ============================
# Товары по категории (AJAX)
# ============================

class ProductsByCategoryView(View):
    def get(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'products': []})
        products = Product.objects.filter(category_id=category_id).values_list('name', flat=True).distinct()
        return JsonResponse({'products': list(products)})


# ============================
# Детальная карточка товара
# ============================

class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['prices'] = ParsedProduct.objects.filter(
            name=self.object.name
        ).order_by('fetched_at').values('fetched_at', 'price')
        return context


# ============================
# Экспорт выбранных товаров в Excel
# ============================

class ExportExcelView(View):
    def post(self, request):
        ids = request.POST.getlist('ids[]')
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Товары"
        ws.append([
            "№", "Наименование", "Ед. изм.", "Цена за ед.", "Входная цена", "Кол-во в упаковке"
        ])

        products = Product.objects.filter(id__in=ids)
        for idx, product in enumerate(products, start=1):
            unit, pack_size = extract_unit_and_pack(product.name)
            price_per_pack = product.avg_price_lemanapro or 0
            price_per_unit = price_per_pack / Decimal(str(pack_size)) if pack_size else price_per_pack
            ws.append([
                idx,
                clean_product_name(product.name),
                unit or 'шт.',
                round(price_per_unit, 2),
                round(price_per_pack, 2),
                pack_size,
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=selected_products.xlsx'
        wb.save(response)
        return response


from django.views.generic import TemplateView
from .models import Product

class IndexView(TemplateView):
    template_name = 'index1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['popular_products'] = Product.objects.order_by('-avg_price_lemanapro')[:8]
        return context
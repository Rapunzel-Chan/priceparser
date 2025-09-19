import re
import json
import openpyxl
from django.views import View
from django.views.generic import TemplateView, ListView
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q, Case, When, Value, IntegerField
from catalog.models import Product, Category
from rapidfuzz import fuzz
from decimal import Decimal
# ============================
# Вспомогательные функции
# ============================

def extract_unit_and_pack(name):
    """Извлекаем единицу измерения и фасовку из названия."""
    match = re.search(r'(\d+[.,]?\d*)\s*(кг|шт|л|м2|м³|г)', name.lower())
    if match:
        pack_size = float(match.group(1).replace(',', '.'))
        unit = match.group(2)
        return unit, pack_size
    return None, 1

def clean_product_name(name):
    """Очищаем название от брендов и кодов."""
    brands = ["церезит", "ce", "40"]
    words = name.split()
    cleaned = [w for w in words if w.lower() not in brands]
    return " ".join(cleaned)


# ============================
# Категории
# ============================

class CategoryListView(ListView):
    model = Category
    template_name = 'categories.html'
    context_object_name = 'categories'


# ============================
# Товары по категории + Поиск
# ============================

class ProductListView(ListView):
    model = Product
    template_name = 'products.html'
    context_object_name = 'products'
    paginate_by = 50

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        queryset = Product.objects.filter(category_id=category_id)

        search = self.request.GET.get('search')
        if search:
            words = search.lower().split()
            first_3 = ' '.join(words[:3]) if len(words) >= 3 else None
            first_5 = ' '.join(words[:5]) if len(words) >= 5 else None

            conditions = []
            if first_3:
                conditions.append(When(name__istartswith=first_3, then=Value(1)))
            if first_5:
                conditions.append(When(name__istartswith=first_5, then=Value(2)))

            queryset = queryset.annotate(
                priority=Case(*conditions, default=Value(99), output_field=IntegerField())
            ).filter(Q(name__icontains=search)).order_by('priority', 'name')
        else:
            queryset = queryset.order_by('name')

        return queryset


# ============================
# Выбор товаров
# ============================

class ProductSelectView(TemplateView):
    template_name = 'index1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()

        selected_category_id = self.request.GET.get('category')
        if selected_category_id:
            products = Product.objects.filter(
                category_id=selected_category_id
            ).values_list('name', flat=True).distinct()
            context['product_names'] = products
            context['product_names_json'] = json.dumps(list(products), ensure_ascii=False)
            context['selected_category_id'] = int(selected_category_id)
        else:
            context['product_names'] = []
            context['product_names_json'] = '[]'

        return context


# ============================
# Вывод на экран с ценой из БД
# ============================

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Получить товары из категории (AJAX)
class ProductsByCategoryView(View):
    def get(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'products': []})
        products = Product.objects.filter(category_id=category_id).values_list('name', flat=True).distinct()
        return JsonResponse({'products': list(products)})


# Обработка итогового списка и отображение с ценами
class ProductResultView(View):
    def post(self, request):
        names = request.POST.getlist('products[]')

        results = []
        for idx, name in enumerate(names, start=1):
            product = Product.objects.filter(name__icontains=name).first()
            if not product:
                avg_price_pack = None
            else:
                avg_price_pack = product.avg_price_lemanapro

            unit, pack_size = extract_unit_and_pack(product.name if product else name)

            if avg_price_pack and pack_size:
                avg_price_unit = avg_price_pack / Decimal(str(pack_size))
            else:
                avg_price_unit = avg_price_pack

            results.append({
                'pp': idx,
                'id': product.id if product else None,
                'name': clean_product_name(product.name if product else name),
                'unit': unit or 'шт.',
                'price_per_unit': round(avg_price_unit, 2) if avg_price_unit else '—',
                'avg_price_pack': round(avg_price_pack, 2) if avg_price_pack else '—',
                'pack_size': pack_size,
            })

        return render(request, 'show_selected_products.html', {'results': results})


# Экспорт в Excel (оставим как у тебя)
class ExportExcelView(View):
    def post(self, request):
        ids = request.POST.getlist('ids[]')
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Товары"
        ws.append([
            "п/п",
            "наименование",
            "ед. изм.",
            "цена за ед. изм. (с доставкой)",
            "пересчет. цена",
            "входная цена",
            "кол-во в упаковке",
            "доставка ед. изм.",
            "цена доставки",
            "партия"
        ])

        products = Product.objects.filter(id__in=ids)
        products_dict = {str(p.id): p for p in products}

        for idx, id_ in enumerate(ids, start=1):
            product = products_dict.get(id_)
            if not product:
                continue

            unit, pack_size = extract_unit_and_pack(product.name)
            price_per_pack = product.avg_price_lemanapro or 0
            price_per_unit = price_per_pack / Decimal(str(pack_size)) if pack_size else price_per_pack

            ws.append([
                idx,
                clean_product_name(product.name),
                unit or "шт.",
                round(price_per_unit, 2),
                round(price_per_unit, 2),
                round(price_per_pack, 2),
                pack_size,
                0,
                0,
                1
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=selected_products.xlsx'
        wb.save(response)
        return response

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

        return redirect('select_products')

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@method_decorator(csrf_exempt, name='dispatch')
class ParseProductView(View):
    def post(self, request):
        data = json.loads(request.body)
        product_name = data.get('name')
        if not product_name:
            return JsonResponse({'error': 'No product name provided'}, status=400)

        # Вызов твоей функции парсера (пример)
        product = parse_lemana_pro(product_name)  # должна возвращать или создавать продукт в БД

        if not product:
            return JsonResponse({'error': 'Parsing failed or product not found'}, status=404)

        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'price': float(product.avg_price_lemanapro or 0)
        })

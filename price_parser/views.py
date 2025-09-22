from django.contrib import messages
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView, CreateView
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from decimal import Decimal
import json
import openpyxl

from .models import Product, Category, ParsedProduct, ParserSchedule
from .utils.price_utils import filtered_unique_mean, extract_unit_and_pack, clean_product_name



# ============================
# Категории (список)
# ============================
class CategoryListView(ListView):
    model = Category
    template_name = 'price_parser/categories.html'
    context_object_name = 'categories'


# ============================
# Выбор товаров + фильтр
# ============================

from django.utils import timezone
from datetime import timedelta

class ProductSelectView(TemplateView):
    template_name = 'price_parser/add_or_select_products.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        category_id = self.request.GET.get('category')
        context['selected_category'] = int(category_id) if category_id and category_id.isdigit() else None
        context['q'] = self.request.GET.get('q', '')
        queryset = Product.objects.all()
        if context['q']:
            queryset = queryset.filter(name__icontains=context['q'])
        if context['selected_category']:
            queryset = queryset.filter(category_id=context['selected_category'])
        context['products'] = queryset.order_by('name')

        # --- добавим выбранные товары ---
        context['selected_products'] = self.request.GET.getlist('selected_products')
        return context



# ============================
# Парсинг одного товара через AJAX
# ============================

import json
from decimal import Decimal
from django.views import View
from django.http import JsonResponse
from price_parser.services.lemana_parse import async_search_multiple_products
import asyncio

# class ParseProductView(View):
#     def post(self, request):
#         data = json.loads(request.body)
#         product_name = data.get('name')
#         if not product_name:
#             return JsonResponse({'error': 'Нет названия'}, status=400)
#
#         async def run_scraper():
#             results = await async_search_multiple_products([product_name])
#             product_results = results.get(product_name)
#             if not product_results or not product_results.get("products"):
#                 return None
#
#             # убираем дубликаты по названию и цене
#             seen = set()
#             unique_items = []
#             for r in product_results["products"]:
#                 key = (r["name"].lower(), Decimal(r["price"]))
#                 if key not in seen:
#                     seen.add(key)
#                     unique_items.append(r)
#
#             prices = [Decimal(r["price"]) for r in unique_items]
#             if not prices:
#                 return None
#
#             # средняя цена без крайних значений
#             from price_parser.utils.price_utils import filtered_unique_mean
#             avg_price = filtered_unique_mean(prices, trim_pct=0.30)
#             return avg_price
#
#         avg_price = asyncio.run(run_scraper())
#
#         if avg_price is None:
#             return JsonResponse({'error': 'Товар не найден'}, status=404)
#
#         return JsonResponse({'avg_price_pack': float(avg_price)})

# ============================
# Парсинг всех выбранных
# ============================

import json
from decimal import Decimal
from django.views import View
from django.http import JsonResponse
from price_parser.services.lemana_parse import async_search_multiple_products
import asyncio

class ParseProductView(View):
    def post(self, request):
        data = json.loads(request.body)
        product_name = data.get('name')
        if not product_name:
            return JsonResponse({'error': 'Нет названия'}, status=400)

        async def run_scraper():
            results = await async_search_multiple_products([product_name])
            product_results = results.get(product_name)
            if not product_results or not product_results.get("products"):
                return None

            # убираем дубликаты по названию и цене
            seen = set()
            unique_items = []
            for r in product_results["products"]:
                key = (r["name"].lower(), Decimal(r["price"]))
                if key not in seen:
                    seen.add(key)
                    unique_items.append(r)

            prices = [Decimal(r["price"]) for r in unique_items]
            if not prices:
                return None

            # средняя цена без крайних значений
            from price_parser.utils.price_utils import filtered_unique_mean
            avg_price = filtered_unique_mean(prices, trim_pct=0.30)
            return avg_price

        avg_price = asyncio.run(run_scraper())

        if avg_price is None:
            return JsonResponse({'error': 'Товар не найден'}, status=404)

        return JsonResponse({'avg_price_pack': float(avg_price)})


# ============================
# Добавление товаров
# ============================

class AddProductsView(View):
    def get(self, request):
        categories = Category.objects.all()
        return render(request, 'add_products.html', {'categories': categories})

    def post(self, request):
        category_id = request.POST.get('category_id')
        category = Category.objects.get(id=category_id)

        product_names = request.POST.getlist('product_names[]')
        pack_sizes = request.POST.getlist('pack_sizes[]')

        for name, pack in zip(product_names, pack_sizes):
            if name.strip():
                Product.objects.get_or_create(
                    name=name.strip(),
                    category=category,
                    pack_size=pack or None,
                    source='leroy_merlen'
                )

        return redirect('price_parser:show_selected_products')


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
    template_name = 'price_parser/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['prices'] = ParsedProduct.objects.filter(product=self.object).order_by('fetched_at').values(
            'fetched_at', 'price')
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
        ws.append(["№", "Наименование", "Ед. изм.", "Цена за ед.", "Цена за упаковку", "Кол-во в упаковке"])
        products = Product.objects.filter(id__in=ids)
        for idx, product in enumerate(products, 1):
            pack_size = product.pack_size or Decimal('1')
            price_pack = product.avg_price_lemanapro or Decimal('0')
            try:
                price_per_unit = (price_pack / Decimal(pack_size)).quantize(Decimal('0.01'))
            except Exception:
                price_per_unit = price_pack
            ws.append([
                idx, clean_product_name(product.name),
                product.unit or "шт.",
                float(price_per_unit),
                float(price_pack),
                float(pack_size),
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        # response['Content-Disposition'] = 'attachment; filename=selected_products.xlsx'
        wb.save(response)
        return response


from django.views.generic import TemplateView
from .models import Product

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product


class IndexView(View):
    template_name = 'price_parser/index1.html'

    def get(self, request):
        popular_products = Product.objects.order_by('-avg_price_lemanapro')[:8]
        parsers = ParserSchedule.objects.filter(is_active=True)
        return render(request, self.template_name, {
            'popular_products': popular_products,
            'parsers': parsers
        })

    def post(self, request):
        platform = request.POST.get('platform')
        interval = request.POST.get('interval')
        auto = request.POST.get('auto') == 'on'
        # сохраняем настройки (можно UserProfile или отдельную модель)
        messages.success(request, "Настройки сохранены")
        return redirect('price_parser:index1')


from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ParserSchedule
from .forms import ParserScheduleForm



# Список парсеров
class ParsersListView(View):
    def get(self, request):
        parsers = ParserSchedule.objects.all()
        return render(request, 'price_parser/parsers.html', {'parsers': parsers})


# Добавление нового парсера
class AddParserView(CreateView):
    model = ParserSchedule
    form_class = ParserScheduleForm
    template_name = 'price_parser/parser_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        if not self.object.manual and self.object.interval:
            self._create_periodic_task(self.object)
        return redirect('price_parser:parser_select_products', pk=self.object.pk)

    def _create_periodic_task(self, parser):
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        import json
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=parser.interval, period='minutes')
        PeriodicTask.objects.update_or_create(
            name=f"parse_parser_{parser.pk}",
            defaults={
                'interval': schedule,
                'task': 'price_parser.tasks.parse_parser_products',
                'args': json.dumps([parser.pk]),
            }
        )


class ParserSelectProductsView(View):
    template_name = 'price_parser/parser_select_products.html'

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, user=request.user)
        products = Product.objects.all()
        return render(request, self.template_name, {'parser': parser, 'products': products})

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, user=request.user)
        selected_ids = request.POST.getlist('products')
        parser.products.set(Product.objects.filter(id__in=selected_ids))
        return redirect('price_parser:products_list')

# Редактирование парсера
class EditParserView(View):
    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        form = ParserScheduleForm(instance=parser)
        return render(request, 'parser_form.html', {'form': form, 'title': 'Редактировать парсер'})

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        form = ParserScheduleForm(request.POST, instance=parser)
        if form.is_valid():
            form.save()
            messages.success(request, "Парсер успешно обновлён")
            return redirect('price_parser:parsers')
        return render(request, 'parser_form.html', {'form': form, 'title': 'Редактировать парсер'})


# Запуск парсера вручную (можно через Celery)
class RunParserNowView(View):
    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        # Тут можно добавить Celery таск для запуска парсера
        # parse_product_task.delay(parser.id)
        parser.last_run = timezone.now()
        parser.save()
        messages.success(request, f"Парсер '{parser.name}' запущен")
        return redirect('price_parser:parsers')

from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Product, ParsedProduct

from .services.lemana_parse import search_lemanapro_products
import asyncio
import logging
from decimal import Decimal

from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

from price_parser.models import Product, ParsedProduct
from price_parser.tasks import parse_products_batch_task
from price_parser.utils.price_utils import filtered_unique_mean
from price_parser.services.lemana_parse import async_search_multiple_products

logger = logging.getLogger(__name__)


from django.shortcuts import render
from django.views import View
from django.contrib import messages
from .models import Product

class ProductSelectActionView(View):
    def get(self, request, *args, **kwargs):
        # Получаем список выбранных товаров из GET-параметров
        selected_products = request.GET.getlist('selected_products')
        # Преобразуем в строковый формат для использования в шаблоне
        selected_products = [str(product_id) for product_id in selected_products]

        # Получаем все товары для отображения
        products = Product.objects.all()

        # Передаем данные в контекст шаблона
        context = {
            'products': products,
            'selected_products': selected_products,
            'q': request.GET.get('q', ''),
            'selected_category': request.GET.get('category', ''),
            'categories': Category.objects.all(),
        }
        return render(request, 'price_parser/add_or_select_products.html', context)

    def post(self, request, *args, **kwargs):
        # Обрабатываем выбранные товары и товары, добавленные вручную
        selected_products = request.POST.getlist('selected_products')
        manual_products = request.POST.get('manual_products', '').split(',')

        # Логика парсинга товаров
        # ...

        # Отображаем сообщение об успешном запуске парсинга
        messages.success(request, 'Парсинг запущен для выбранных и новых товаров.')
        return redirect('price_parser:product_select')






# ============================
# Результаты парсинга
# ============================

from django.views.generic import ListView

class ResultsView(ListView):
    model = Product
    template_name = 'price_parser/show_selected_products.html'
    context_object_name = 'products'

    def get_queryset(self):
        ids = self.request.session.get('parsed_products_ids', [])
        return Product.objects.filter(id__in=ids)



class ProductListView(ListView):
    model = Product
    template_name = 'price_parser/products_list.html'
    context_object_name = 'products'
    ordering = ['-avg_price_lemanapro']


from django.views.generic import TemplateView
from django.db.models import F, Subquery, OuterRef, Avg
from .models import Product, ParsedProduct
from datetime import timedelta
from django.utils import timezone

class ReportsView(TemplateView):
    template_name = "price_parser/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Рассчитаем % изменение по каждому продукту: сравнить среднюю за 30 дней и среднюю за предыдущие 30 дней
        now = timezone.now()
        last_30 = now - timedelta(days=30)
        prev_60 = now - timedelta(days=60)

        products = Product.objects.all()
        report_items = []
        for p in products:
            new_avg_qs = ParsedProduct.objects.filter(product=p, fetched_at__gte=last_30)
            prev_avg_qs = ParsedProduct.objects.filter(product=p, fetched_at__gte=prev_60, fetched_at__lt=last_30)

            new_avg = new_avg_qs.aggregate(avg=Avg('price'))['avg'] or 0
            prev_avg = prev_avg_qs.aggregate(avg=Avg('price'))['avg'] or 0

            if prev_avg:
                change_pct = ((new_avg - prev_avg) / prev_avg) * 100
            else:
                change_pct = None

            report_items.append({
                "product": p,
                "new_avg": new_avg,
                "prev_avg": prev_avg,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "popularity": p.popularity or 0
            })

        context['report_items'] = sorted(report_items, key=lambda x: (x['change_pct'] is None, -(x['change_pct'] or 0)))[:100]
        return context

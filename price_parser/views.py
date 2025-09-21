from django.contrib import messages
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from decimal import Decimal
import json
import openpyxl

from .models import Product, Category, ParsedProduct, ParserSchedule
from .utils.price_utils import filtered_unique_mean, extract_unit_and_pack, clean_product_name
from .services.lemana_pro_parser import LemanaProScraper
from .tasks import parse_product_task


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
    """
    Запуск асинхронного парсинга выбранных товаров через Celery
    и обновление основной модели Product.
    """
    def post(self, request, *args, **kwargs):
        selected_products = request.POST.getlist("selected_products")  # список ID товаров

        for pid in selected_products:
            try:
                product = Product.objects.get(id=pid)
            except Product.DoesNotExist:
                continue

            # Асинхронно через Celery
            result = parse_product_task.delay(pid)  # результат парсера (Celery)
            # Если хочешь синхронно (для теста), можно:
            # result = parse_product_task(pid)

            # Допустим, parse_product_task возвращает dict с avg_price, unit, pack_size
            # После выполнения задачи обновляем Product
            parsed_data = result.get()  # если синхронно
            if parsed_data:
                product.avg_price_lemanapro = parsed_data.get('avg_price') or product.avg_price_lemanapro
                product.unit = parsed_data.get('unit') or product.unit
                product.pack_size = parsed_data.get('pack_size') or product.pack_size
                product.save()

        messages.success(request, "Парсинг запущен. Результаты появятся позже.")
        return redirect("price_parser:show_selected_products")




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

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product

class IndexView(View):
    template_name = 'index1.html'

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
from .tasks import parse_product_task  # если нужно запускать Celery для теста

# Список парсеров
class ParsersListView(View):
    def get(self, request):
        parsers = ParserSchedule.objects.all()
        return render(request, 'parsers.html', {'parsers': parsers})

# Добавление нового парсера
class AddParserView(View):
    def get(self, request):
        form = ParserScheduleForm()
        return render(request, 'parser_form.html', {'form': form, 'title': 'Добавить парсер'})

    def post(self, request):
        form = ParserScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Парсер успешно добавлен")
            return redirect('price_parser:parsers')
        return render(request, 'parser_form.html', {'form': form, 'title': 'Добавить парсер'})

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


class ProductSelectActionView(View):
    def post(self, request):
        selected_ids = request.POST.getlist('selected_products')
        manual_names = request.POST.getlist('manual_products[]')

        for name in manual_names:
            if name.strip():
                Product.objects.get_or_create(name=name.strip())

        for pid in selected_ids:
            if Product.objects.filter(id=pid).exists():
                parse_product_task.delay(pid)  # Celery парсинг
        messages.success(request, "Парсинг запущен")
        return redirect('price_parser:results')


class ResultsView(ListView):
    model = ParsedProduct
    template_name = 'results.html'
    context_object_name = 'results'
    ordering = ['fetched_at']

    def get_queryset(self):
        return ParsedProduct.objects.all().order_by('fetched_at')


class ProductListView(ListView):
    model = Product
    template_name = 'products_list.html'
    context_object_name = 'products'
    ordering = ['-avg_price_lemanapro']

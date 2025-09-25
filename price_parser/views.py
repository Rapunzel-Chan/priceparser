from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView, CreateView
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q
from decimal import Decimal
import json
import openpyxl
from django.views.generic import TemplateView
from django.db.models import F, Subquery, OuterRef, Avg
from .models import Product, ParsedProduct
from datetime import timedelta
from django.utils import timezone
from .models import Product, Category, ParsedProduct, ParserSchedule
from .utils.price_utils import filtered_unique_mean, extract_unit_and_pack, clean_product_name
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.http import JsonResponse
from price_parser.services.lemana_service import lemana_parse_saved
from django.views.generic import TemplateView
from .models import Product
import json
from decimal import Decimal
from django.views import View
from django.http import JsonResponse
# from price_parser.services.lemana_parse import async_search_multiple_products
import asyncio
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Product
from django.views import View
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse
from openpyxl import Workbook
from price_parser.models import Product, ParsedProduct

from django.views import View
from django.http import HttpResponse
from openpyxl import Workbook
from django.utils import timezone
from price_parser.models import Product
from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack

from django.shortcuts import render
from django.views import View
from django.http import HttpResponse
from openpyxl import Workbook
from django.utils import timezone
from .models import Product

from django.views import View
from django.shortcuts import render
from django.utils import timezone
from price_parser.models import Product
from price_parser.utils.price_utils import filtered_unique_mean, extract_unit_and_pack



from django.views import View
from django.http import HttpResponse
from openpyxl import Workbook
from price_parser.models import ParsedProduct
from price_parser.utils.price_utils import extract_unit_and_pack


from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ParserSchedule
from .forms import ParserScheduleForm





from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Product, ParsedProduct


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


logger = logging.getLogger(__name__)
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib import messages
from .models import Product
from .tasks import parse_products_batch_task


class IndexView(View):
    """Главная страница"""
    template_name = 'price_parser/index1.html'

    def get(self, request):
        popular_products = Product.objects.order_by('-avg_price_lemanapro')[:8]
        parsers = ParserSchedule.objects.filter(is_active=True)
        return render(request, self.template_name, {
            'popular_products': popular_products,
            'parsers': parsers
        })

    # def post(self, request):
    #     platform = request.POST.get('platform')
    #     interval = request.POST.get('interval')
    #     auto = request.POST.get('auto') == 'on'
    #     # сохраняем настройки (можно UserProfile или отдельную модель)
    #     messages.success(request, "Настройки сохранены")
    #     return redirect('price_parser:index1')


class ProductListView(LoginRequiredMixin, ListView):
    """Список продуктов(каталог)"""
    model = Product
    template_name = 'price_parser/products_list.html'
    context_object_name = 'products'
    ordering = ['-avg_price_lemanapro']

    def get_queryset(self):

        if self.request.user.is_superuser:
            return Product.objects.all().order_by('-avg_price_lemanapro')
        return Product.objects.filter(owner=self.request.user).order_by('-avg_price_lemanapro')
        # if self.request.user.is_superuser:
        #     return Product.objects.all()
        # return Product.objects.filter(owner=self.request.user)

    # def get_queryset(self):
    #     qs = Product.objects.all() if self.request.user.is_superuser else Product.objects.filter(owner=self.request.user)
    #     return qs.order_by('-avg_price_lemanapro')

class ProductDetailView(LoginRequiredMixin, DetailView):
    """Детальная карточка товара"""
    model = Product
    template_name = 'price_parser/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['prices'] = ParsedProduct.objects.filter(product=self.object).order_by('fetched_at').values(
            'fetched_at', 'price', 'pack_size', 'unit'
        )
        return context

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Product.objects.all()
        return Product.objects.filter(owner=self.request.user)


class CategoryListView(ListView):
    """Список категорий"""
    model = Category
    template_name = 'price_parser/categories.html'
    context_object_name = 'categories'


class ProductSelectView(LoginRequiredMixin, TemplateView):
    """Выбор товаров"""
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

class ProductSelectActionView(LoginRequiredMixin, View):
    """
    Обработка выбора/добавления товаров:
    - сохраняем выбранные товары в сессии,
    - запускаем парсинг через Celery,
    - возвращаем статус.
    """

    def post(self, request, *args, **kwargs):
        # Получаем выбранные товары с формы
        selected_products = request.POST.getlist('selected_products')
        manual_products = request.POST.get('manual_products', '').splitlines()

        # Создаём новые товары из ручного ввода
        new_product_ids = []
        for name in manual_products:
            name = name.strip()
            if not name:
                continue
            product, created = Product.objects.get_or_create(name=name, defaults={'owner': request.user})
            # если продукт существует, но не привязан к владельцу — можно назначить
            if not product.owner:
                product.owner = request.user
                product.save()
            new_product_ids.append(product.id)

        # Объединяем ID (строки -> int)
        all_ids = []
        for sid in selected_products + [str(pid) for pid in new_product_ids]:
            try:
                all_ids.append(int(sid))
            except Exception:
                continue

        # Все ID товаров для парсинга
        #all_ids = selected_products + [str(pid) for pid in new_product_ids]

        # Сохраняем выбранные товары в сессии
        if all_ids:
            request.session['selected_products_ids'] = all_ids
            request.session.modified = True

            # Запускаем Celery-задачу
            task = parse_products_batch_task.delay(all_ids, user_id=request.user.id) #owner
            request.session['task_id'] = task.id
            request.session.modified = True

            # Сообщение для пользователя
            messages.info(request, "Ожидайте, парсер запущен…")

        return JsonResponse({'status': 'started'})


class ParsingStatusView(LoginRequiredMixin, View):
    """
    Проверка статуса запущенной задачи Celery.
    Для фронта, чтобы показать кругляш ожидания.
    """
    def get(self, request):
        task_id = request.session.get('task_id')
        if not task_id:
            return JsonResponse({'done': True})

        from celery.result import AsyncResult
        res = AsyncResult(task_id)
        return JsonResponse({'done': res.ready()})


class ParseProductView(LoginRequiredMixin, View):
    """
    Синхронный парсинг одного продукта через LemanaPro.
    Сохраняет ParsedProduct, ParsedProductArchive и обновляет Product.
    """
    def post(self, request):
        import json
        data = json.loads(request.body)
        product_name = data.get("name")

        if not product_name:
            return JsonResponse({"error": "Нет названия"}, status=400)

        # Вызываем функцию, которая делает весь парсинг и сохранение
        avg_price_per_unit = lemana_parse_saved(product_name)

        if avg_price_per_unit is None:
            return JsonResponse({"error": "Товар не найден"}, status=404)

        return JsonResponse({
            "message": f"Продукт '{product_name}' успешно пропарсен",
            "avg_price_per_unit": float(avg_price_per_unit)
        })


class ParsersListView(LoginRequiredMixin, View):
    """Список парсеров"""
    model = ParserSchedule
    template_name = 'price_parser/parsers.html'
    context_object_name = 'parsers'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return ParserSchedule.objects.all()
        return ParserSchedule.objects.filter(owner=self.request.user) #owner

    def get(self, request):
        # parsers = ParserSchedule.objects.all()
        # return render(request, 'price_parser/parsers.html', {'parsers': parsers})
        parsers = self.get_queryset()
        return render(request, self.template_name, {'parsers': parsers})

class AddParserView(LoginRequiredMixin, CreateView):
    """Добавление нового парсера"""
    model = ParserSchedule
    form_class = ParserScheduleForm
    template_name = 'price_parser/parser_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        # if not self.object.manual and self.object.interval:
        #     self._create_periodic_task(self.object)
        return redirect('price_parser:parser_select_products', pk=self.object.pk)

    # def _create_periodic_task(self, parser):
    #     from django_celery_beat.models import PeriodicTask, IntervalSchedule
    #     import json
    #     schedule, _ = IntervalSchedule.objects.get_or_create(
    #         every=parser.interval, period='minutes')
    #     PeriodicTask.objects.update_or_create(
    #         name=f"parse_parser_{parser.pk}",
    #         defaults={
    #             'interval': schedule,
    #             'task': 'price_parser.tasks.parse_parser_products',
    #             'args': json.dumps([parser.pk]),
    #         }
    #     )


class ParserSelectProductsView(LoginRequiredMixin, View):
    """Парсер, связанный с выбранным продуктом"""
    template_name = 'price_parser/parser_select_products.html'

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user) #owner
        products = Product.objects.filter(owner=request.user)
        if not products.exists():
            # если нет продуктов, можно редиректить на add_or_select_products
            messages.info(request, "Выберите продукты для парсинга")
            return redirect('price_parser:add_or_select_products')
        return render(request, self.template_name, {'parser': parser, 'products': products})

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user)
        selected_ids = request.POST.getlist('products')
        parser.products.set(Product.objects.filter(id__in=selected_ids, owner=request.user))
        parser.save()
        return redirect('price_parser:products_list')


class EditParserView(LoginRequiredMixin, View):
    """Редактирование созданного парсера"""
    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        if parser.owner != request.user:
            raise Http404("Нет доступа к этому парсеру")
        form = ParserScheduleForm(instance=parser)
        return render(request, 'parser_form.html', {'form': form, 'title': 'Редактировать парсер'})

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        if parser.owner != request.user:
            raise Http404("Нет доступа к этому парсеру")
        form = ParserScheduleForm(request.POST, instance=parser)
        if form.is_valid():
            form.save()
            messages.success(request, "Парсер успешно обновлён")
            return redirect('price_parser:parsers')
        return render(request, 'parser_form.html', {'form': form, 'title': 'Редактировать парсер'})


class RunParserNowView(LoginRequiredMixin, View):
    """Запуск парсера вручную"""

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user) #owner
        product_ids = list(parser.products.values_list('id', flat=True))
        if not product_ids:
            messages.error(request, "Нет продуктов в парсере — добавьте продукты перед запуском.")
            return redirect('price_parser:parsers')
        parse_products_batch_task.delay(product_ids, user_id=request.user.id) #owner
        parser.last_run = timezone.now()
        parser.save()
        messages.success(request, f"Парсер '{parser.name}' запущен")
        return redirect('price_parser:parsers')


class ResultsView(LoginRequiredMixin, View):
    """
    Отображение результатов парсинга — только выбранные продукты.
    """
    template_name = "price_parser/show_selected_products.html"

    def get(self, request):
        # Берём только выбранные продукты из сессии
        selected_ids = request.session.get('selected_products_ids', [])
        products = Product.objects.filter(id__in=selected_ids)
        table_data = []

        for prod in products:
            last_parsed = prod.parsed_products.order_by("-fetched_at").first()
            if not last_parsed:
                continue  # если ещё нет пропарсенного товара, пропускаем

            pack_size = last_parsed.pack_size or prod.pack_size or 1
            unit = last_parsed.unit or prod.unit or "шт."
            all_prices = prod.parsed_products.values_list("price", flat=True)
            avg_price_pack = filtered_unique_mean([p for p in all_prices if p is not None]) or 0
            price_per_unit = avg_price_pack / pack_size if pack_size else avg_price_pack
            source = last_parsed.source
            fetched_at = last_parsed.fetched_at
            if timezone.is_aware(fetched_at):
                fetched_at = timezone.make_naive(fetched_at)
            url = last_parsed.url

            table_data.append({
                "product_id": prod.id,
                "product_name": prod.name,
                "pack_size": pack_size,
                "unit": unit,
                "avg_price_pack": avg_price_pack,
                "price_per_unit": price_per_unit,
                "source": last_parsed.source,
                "fetched_at": fetched_at,
                "url": last_parsed.url,
            })

            return render(request, self.template_name, {"table_data": table_data})


class ExportSummaryExcelView(LoginRequiredMixin, View):
    """
    Сводный отчет — агрегировано по Product.
    """
    def post(self, request):
        ids = request.POST.getlist("ids[]")
        products = Product.objects.filter(id__in=ids)

        wb = Workbook()
        ws = wb.active
        ws.title = "Сводный отчет"
        ws.append([
            "Наименование", "Фасовка", "Ед. изм.",
            "Средняя цена, ₽", "Цена за ед., ₽",
            "Источник", "Дата парсинга", "URL"
        ])

        for prod in products:
            last_parsed = prod.parsed_products.order_by("-fetched_at").first()

            pack_size = last_parsed.pack_size or prod.pack_size or 1
            unit = last_parsed.unit or prod.unit or "шт."
            avg_price_pack = filtered_unique_mean(prod.parsed_products.values_list("price", flat=True)) or 0
            price_per_unit = (avg_price_pack / pack_size) if pack_size else avg_price_pack
            source = last_parsed.source if last_parsed else prod.source
            fetched_at = last_parsed.fetched_at if last_parsed else timezone.now()
            if timezone.is_aware(fetched_at):
                fetched_at_naive = timezone.make_naive(fetched_at)
            url = last_parsed.url if last_parsed else ""

            ws.append([
                prod.name,
                pack_size,
                unit,
                float(avg_price_pack),
                float(price_per_unit),
                source,
                fetched_at_naive,
                url
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename=summary.xlsx'
        wb.save(response)
        return response


class ExportDetailedExcelView(LoginRequiredMixin, View):
    """
    Детальный отчет — все ParsedProduct для выбранных Product.
    """
    def post(self, request):
        ids = request.POST.getlist("ids[]")
        parsed_products = ParsedProduct.objects.filter(product_id__in=ids).order_by("name")

        wb = Workbook()
        ws = wb.active
        ws.title = "Детальный отчет"
        ws.append([
            "Наименование", "Фасовка", "Ед. изм.", "Цена за ед., ₽",
            "Цена за упаковку", "URL", "Источник", "Дата парсинга"
        ])

        for pp in parsed_products:
            pack_size = pp.pack_size or 1
            unit = pp.unit or "шт."
            price_per_unit = (pp.price / pack_size) if pp.price else 0
            price_pack = pp.price or 0
            fetched_at_naive = pp.fetched_at
            if timezone.is_aware(fetched_at_naive):
                fetched_at_naive = timezone.make_naive(fetched_at_naive)
            ws.append([
                pp.name,
                pack_size,
                unit,
                float(price_per_unit),
                float(price_pack),
                pp.url or "",
                pp.source,
                fetched_at_naive
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename=detailed.xlsx'
        wb.save(response)
        return response


class ReportsView(LoginRequiredMixin, TemplateView):
    """Отображение отчетов по пропарсенным продуктам"""
    template_name = "price_parser/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Рассчитаем % изменение по каждому продукту: сравнить среднюю за 30 дней и среднюю за предыдущие 30 дней
        now = timezone.now()
        last_3 = now - timedelta(days=3)
        prev_6 = now - timedelta(days=6)

        products = Product.objects.filter(owner=self.request.user)
        report_items = []
        for p in products:
            new_avg = ParsedProduct.objects.filter(product=p, fetched_at__gte=last_3).aggregate(avg=Avg('price'))['avg'] or 0
            prev_avg = ParsedProduct.objects.filter(product=p, fetched_at__gte=prev_6, fetched_at__lt=last_3).aggregate(avg=Avg('price'))['avg'] or 0
            change_pct = ((new_avg - prev_avg) / prev_avg * 100) if prev_avg else None
            # new_avg = new_avg_qs.aggregate(avg=Avg('price'))['avg'] or 0
            # prev_avg = prev_avg_qs.aggregate(avg=Avg('price'))['avg'] or 0

            # if prev_avg:
            #     change_pct = ((new_avg - prev_avg) / prev_avg) * 100
            # else:
            #     change_pct = None

            report_items.append({
                "product": p,
                "new_avg": new_avg,
                "prev_avg": prev_avg,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "popularity": p.popularity or 0
            })

        context['report_items'] = sorted(report_items, key=lambda x: (x['change_pct'] is None, -(x['change_pct'] or 0)))[:100] #context['report_items'] = report_items
        return context

# ============================
# Парсинг одного товара через AJAX
# ============================



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
# Добавление товаров
# ============================

# class AddProductsView(View):
#     def get(self, request):
#         categories = Category.objects.all()
#         return render(request, 'add_products.html', {'categories': categories})
#
#     def post(self, request):
#         category_id = request.POST.get('category_id')
#         category = Category.objects.get(id=category_id)
#
#         product_names = request.POST.getlist('product_names[]')
#         pack_sizes = request.POST.getlist('pack_sizes[]')
#
#         for name, pack in zip(product_names, pack_sizes):
#             if name.strip():
#                 Product.objects.get_or_create(
#                     name=name.strip(),
#                     category=category,
#                     pack_size=pack or None,
#                     source='leroy_merlen'
#                 )
#
#         return redirect('price_parser:show_selected_products')


# ============================
# Товары по категории (AJAX)
# ============================

# class ProductsByCategoryView(View):
#     def get(self, request):
#         category_id = request.GET.get('category_id')
#         if not category_id:
#             return JsonResponse({'products': []})
#         products = Product.objects.filter(category_id=category_id).values_list('name', flat=True).distinct()
#         return JsonResponse({'products': list(products)})









# class ProductSelectActionView(View):
#     def get(self, request, *args, **kwargs):
#         # Получаем список выбранных товаров из GET-параметров
#         selected_products = request.GET.getlist('selected_products')
#         # Преобразуем в строковый формат для использования в шаблоне
#         selected_products = [str(product_id) for product_id in selected_products]
#
#         # Получаем все товары для отображения
#         products = Product.objects.all()
#
#         # Передаем данные в контекст шаблона
#         context = {
#             'products': products,
#             'selected_products': selected_products,
#             'q': request.GET.get('q', ''),
#             'selected_category': request.GET.get('category', ''),
#             'categories': Category.objects.all(),
#         }
#         return render(request, 'price_parser/add_or_select_products.html', context)
#
#     def post(self, request, *args, **kwargs):
#         selected_products = request.POST.getlist('selected_products')
#         manual_products = request.POST.get('manual_products', '').split(',')
#
#         for name in manual_products:
#             name = name.strip()
#             if name:
#                 Product.objects.get_or_create(name=name)
#
#         if selected_products:
#             parse_products_batch_task.delay(selected_products)
#
#         messages.success(request, 'Парсинг запущен для выбранных и новых товаров.')
#         return redirect('price_parser:add_or_select_products')







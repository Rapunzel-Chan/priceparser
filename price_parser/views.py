import logging
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, View
from openpyxl import Workbook
from rest_framework.reverse import reverse_lazy

from price_parser.services.lemana_service import lemana_parse_saved

from .forms import ParserScheduleForm
from .models import Category, Contacts, ParsedProduct, ParserSchedule, Product
from .tasks import parse_products_batch_task
from .utils.price_utils import filtered_unique_mean

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    """Отображает главную страницу."""

    template_name = "price_parser/index1.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        popular_products = (
            Product.objects.filter(avg_price_lemanapro__isnull=False)
            .order_by("-popularity")
            .select_related("category")[:8]
        )

        if not popular_products.exists():
            popular_products = Product.objects.order_by("-popularity").select_related("category")[:8]

        context["popular_products"] = popular_products
        return context


class CategoryListView(ListView):
    """Отображает список категорий"""

    model = Category
    template_name = "price_parser/categories.html"
    context_object_name = "categories"


class ProductListView(LoginRequiredMixin, ListView):
    """Отображает список продуктов (каталог)."""

    model = Product
    template_name = "price_parser/products_list.html"
    context_object_name = "products"
    ordering = ["-avg_price_lemanapro"]

    def get_queryset(self):
        qs = (
            Product.objects.all()
            if self.request.user.is_superuser
            else Product.objects.filter(owner=self.request.user)
        )
        return qs.order_by("-avg_price_lemanapro")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products_info = []

        for prod in context["products"]:
            last_parsed = prod.parsed_products.order_by("-fetched_at").first()
            if not last_parsed:
                continue

            avg_price_per_unit = prod.avg_price_lemanapro or Decimal("0")

            pack_size = last_parsed.pack_size or Decimal("1")
            unit = last_parsed.unit or "шт"

            avg_price_pack = avg_price_per_unit * pack_size

            products_info.append(
                {
                    "product": prod,
                    "pack_size": pack_size,
                    "unit": unit,
                    "avg_price_pack": avg_price_pack,
                    "price_per_unit": avg_price_per_unit,
                    "last_fetched": last_parsed.fetched_at,
                }
            )

        context["products_info"] = products_info


class ProductDetailView(DetailView):
    """Отображает карточки продуктовв"""

    model = Product
    template_name = "price_parser/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        last_parsed = product.parsed_products.order_by("-fetched_at").first()
        context["last_parsed"] = last_parsed

        today = timezone.now().date()
        context["has_today_record"] = product.price_history.filter(date=today).exists()

        thirty_days_ago = today - timezone.timedelta(days=30)
        price_history = product.price_history.filter(date__gte=thirty_days_ago).order_by("date")

        labels = []
        data = []
        history_with_changes = []

        history_list = list(price_history)
        for i, history in enumerate(history_list):
            labels.append(history.date.strftime("%Y-%m-%d"))
            data.append(float(history.avg_price_per_unit))

            change = None
            if i > 0:
                change = history.avg_price_per_unit - history_list[i - 1].avg_price_per_unit

            history_with_changes.append(
                {"date": history.date, "avg_price_per_unit": history.avg_price_per_unit, "change": change}
            )

        context["labels"] = labels
        context["data"] = data
        context["history_with_changes"] = history_with_changes

        return context


class ProductSelectView(LoginRequiredMixin, TemplateView):
    """Отображение выбора продуктов"""

    template_name = "price_parser/add_or_select_products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        category_id = self.request.GET.get("category")
        context["selected_category"] = int(category_id) if category_id and category_id.isdigit() else None
        context["q"] = self.request.GET.get("q", "")
        queryset = Product.objects.all()
        if context["q"]:
            queryset = queryset.filter(name__icontains=context["q"])
        if context["selected_category"]:
            queryset = queryset.filter(category_id=context["selected_category"])
        context["products"] = queryset.order_by("name")

        context["selected_products"] = self.request.GET.getlist("selected_products")
        return context


class ProductSelectActionView(LoginRequiredMixin, View):
    """Обрабатывает выбор/добавление продуктов."""

    def post(self, request, *args, **kwargs):
        selected_products = request.POST.getlist("selected_products")
        manual_products = request.POST.get("manual_products", "").splitlines()

        new_product_ids = []
        for name in manual_products:
            name = name.strip()
            if not name:
                continue
            product, created = Product.objects.get_or_create(name=name, defaults={"owner": request.user})

            if not product.owner:
                product.owner = request.user
                product.save()
            new_product_ids.append(product.id)

        all_ids = []
        for sid in selected_products + [str(pid) for pid in new_product_ids]:
            try:
                all_ids.append(int(sid))
            except Exception:
                continue

        if all_ids:
            request.session["selected_products_ids"] = all_ids
            request.session.modified = True

            task = parse_products_batch_task.delay(all_ids, user_id=request.user.id)  # owner
            request.session["task_id"] = task.id
            request.session.modified = True

            messages.info(request, "Ожидайте, парсер запущен…")

        return JsonResponse({"status": "started"})


class ParsingStatusView(LoginRequiredMixin, View):
    """Проверяет статус запущенной задачи Celery."""

    def get(self, request):
        task_id = request.session.get("task_id")
        if not task_id:
            return JsonResponse({"done": True})

        from celery.result import AsyncResult

        res = AsyncResult(task_id)
        return JsonResponse({"done": res.ready()})


class ParseProductView(LoginRequiredMixin, View):
    """Парсит по одному продукты через LemanaPro."""

    def post(self, request):
        import json

        data = json.loads(request.body)
        product_name = data.get("name")

        if not product_name:
            return JsonResponse({"error": "Нет названия"}, status=400)

        avg_price_per_unit = lemana_parse_saved(product_name)

        if avg_price_per_unit is None:
            return JsonResponse({"error": "Товар не найден"}, status=404)

        return JsonResponse(
            {"message": f"Продукт '{product_name}' успешно пропарсен", "avg_price_per_unit": float(avg_price_per_unit)}
        )


class ParsersListView(LoginRequiredMixin, View):
    """Отображает список парсеров"""

    model = ParserSchedule
    template_name = "price_parser/parsers.html"
    context_object_name = "parsers"

    def get_queryset(self):
        if self.request.user.is_superuser:
            return ParserSchedule.objects.all()
        return ParserSchedule.objects.filter(owner=self.request.user)  # owner

    def get(self, request):
        parsers = self.get_queryset()
        return render(request, self.template_name, {"parsers": parsers})


class AddParserView(LoginRequiredMixin, CreateView):
    """Добавляет новый парсер"""

    model = ParserSchedule
    form_class = ParserScheduleForm
    template_name = "price_parser/parser_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        return redirect("price_parser:parser_select_products", pk=self.object.pk)


class ParserSelectProductsView(LoginRequiredMixin, View):
    """Предоставляет выбор продуктов, связанных с парсером по расписанию."""

    template_name = "price_parser/parser_select_products.html"

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user)
        products = Product.objects.filter(owner=request.user)

        if not products.exists():
            messages.info(request, "Выберите продукты для парсинга")
            return redirect("price_parser:add_or_select_products")

        selected_ids = list(parser.products.values_list("id", flat=True))

        return render(
            request,
            self.template_name,
            {
                "parser": parser,
                "products": products,
                "selected_ids": selected_ids,  # <---
            },
        )

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user)
        selected_ids = request.POST.getlist("products")
        parser.products.set(Product.objects.filter(id__in=selected_ids, owner=request.user))
        parser.save()
        return redirect("price_parser:products_list")


class EditParserView(LoginRequiredMixin, View):
    """Редактирует созданный парсер."""

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        if parser.owner != request.user:
            raise Http404("Нет доступа к этому парсеру")
        form = ParserScheduleForm(instance=parser)
        return render(request, "price_parser/parser_form.html", {"form": form, "title": "Редактировать парсер"})

    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk)
        if parser.owner != request.user:
            raise Http404("Нет доступа к этому парсеру")
        form = ParserScheduleForm(request.POST, instance=parser)
        if form.is_valid():
            form.save()
            messages.success(request, "Парсер успешно обновлён")
            return redirect("price_parser:parsers")
        return render(request, "parser_form.html", {"form": form, "title": "Редактировать парсер"})


class RunParserNowView(LoginRequiredMixin, View):
    """Запуск парсера вручную"""

    def get(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user)
        product_ids = list(parser.products.values_list("id", flat=True))
        if not product_ids:
            messages.error(request, "Нет продуктов в парсере — добавьте продукты перед запуском.")
            return redirect("price_parser:parsers")

        parse_products_batch_task.delay(product_ids, user_id=request.user.id, parser_id=parser.id)
        parser.last_run = timezone.now()
        parser.save()
        messages.success(request, f"Парсер '{parser.name}' запущен")
        return redirect("price_parser:parsers")


class ResultsView(LoginRequiredMixin, View):
    """Отображает результаты парсинга."""

    template_name = "price_parser/show_selected_products.html"

    def get(self, request):
        selected_ids = request.session.get("selected_products_ids", [])
        products = Product.objects.filter(id__in=selected_ids)
        table_data = []

        for prod in products:
            last_parsed = prod.parsed_products.order_by("-fetched_at").first()
            if not last_parsed:
                continue

            avg_price_per_unit = prod.avg_price_lemanapro or Decimal("0")

            pack_size = last_parsed.pack_size or Decimal("1")
            unit = last_parsed.unit or "шт"

            avg_price_pack = avg_price_per_unit * pack_size

            table_data.append(
                {
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "pack_size": pack_size,
                    "unit": unit,
                    "avg_price_pack": avg_price_pack,
                    "price_per_unit": avg_price_per_unit,
                    "source": last_parsed.source,
                    "fetched_at": last_parsed.fetched_at,
                    "url": last_parsed.url,
                }
            )

        return render(request, self.template_name, {"table_data": table_data})


class DeleteParserView(LoginRequiredMixin, View):
    def post(self, request, pk):
        parser = get_object_or_404(ParserSchedule, pk=pk, owner=request.user)
        parser.delete()
        messages.success(request, "Парсер успешно удалён")
        return redirect("price_parser:parsers")


class ExportSummaryExcelView(LoginRequiredMixin, View):
    """Формирует сводный отчет — агрегировано по Product."""

    def post(self, request):
        ids = request.POST.getlist("ids[]")
        products = Product.objects.filter(id__in=ids)

        wb = Workbook()
        ws = wb.active
        ws.title = "Сводный отчет"
        ws.append(
            [
                "Наименование",
                "Фасовка",
                "Ед. изм.",
                "Средняя цена, ₽",
                "Цена за ед., ₽",
                "Источник",
                "Дата парсинга",
                "URL",
            ]
        )

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

            ws.append(
                [
                    prod.name,
                    pack_size,
                    unit,
                    float(avg_price_pack),
                    float(price_per_unit),
                    source,
                    fetched_at_naive,
                    url,
                ]
            )

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=summary.xlsx"
        wb.save(response)
        return response


class ExportDetailedExcelView(LoginRequiredMixin, View):
    """Формирует детальный отчет — все ParsedProduct для выбранных Product."""

    def post(self, request):
        ids = request.POST.getlist("ids[]")
        parsed_products = ParsedProduct.objects.filter(product_id__in=ids).order_by("name")

        wb = Workbook()
        ws = wb.active
        ws.title = "Детальный отчет"
        ws.append(
            [
                "Наименование",
                "Фасовка",
                "Ед. изм.",
                "Цена за ед., ₽",
                "Цена за упаковку",
                "URL",
                "Источник",
                "Дата парсинга",
            ]
        )

        for pp in parsed_products:
            pack_size = pp.pack_size or 1
            unit = pp.unit or "шт."
            price_per_unit = (pp.price / pack_size) if pp.price else 0
            price_pack = pp.price or 0
            fetched_at_naive = pp.fetched_at
            if timezone.is_aware(fetched_at_naive):
                fetched_at_naive = timezone.make_naive(fetched_at_naive)
            ws.append(
                [
                    pp.name,
                    pack_size,
                    unit,
                    float(price_per_unit),
                    float(price_pack),
                    pp.url or "",
                    pp.source,
                    fetched_at_naive,
                ]
            )

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=detailed.xlsx"
        wb.save(response)
        return response


class ReportsView(LoginRequiredMixin, TemplateView):
    """Отображает отчеты про работе парсеров по расписанию."""

    template_name = "price_parser/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.filter(owner=self.request.user)
        report_items = []

        for p in products:
            last_parsed = p.parsed_products.order_by("-fetched_at").first()
            current_avg = p.avg_price_lemanapro
            from_history = False
            prev_avg = None
            change_pct = None

            if not current_avg:
                last_history = p.price_history.order_by("-date").first()
                if last_history:
                    current_avg = last_history.avg_price_per_unit
                    from_history = True

            if current_avg:
                prev_history = p.price_history.exclude(date=timezone.now().date()).order_by("-date").first()
                if prev_history:
                    prev_avg = prev_history.avg_price_per_unit
                    if prev_avg > 0:
                        change_pct = round(((current_avg - prev_avg) / prev_avg) * 100, 2)

            report_items.append(
                {
                    "product": p,
                    "new_avg": round(current_avg, 2) if current_avg else None,
                    "prev_avg": round(prev_avg, 2) if prev_avg else None,
                    "change_pct": change_pct,
                    "popularity": p.popularity or 0,
                    "source": last_parsed.source if last_parsed else "",
                    "from_history": from_history,
                }
            )

        context["report_items"] = sorted(
            report_items, key=lambda x: (x["change_pct"] is None, -(x["change_pct"] or 0))
        )
        return context


class ContactsView(TemplateView):
    """Отобажает контакты и форму обратной связи."""

    template_name = "price_parser/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contacts = Contacts.objects.first()
        context["contacts"] = contacts
        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name")
        message = request.POST.get("message")
        phone = request.POST.get("phone")

        if name and phone and message:
            try:
                subject = f"Новое сообщение от {name}"
                body = f"Имя: {name}\n" f"Телефон: {phone}\n" f"Сообщение:\n{message}"

                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )

                messages.success(request, "Спасибо! Ваше сообщение успешно отправлено.")
            except Exception as e:
                messages.error(request, f"Ошибка отправки: {str(e)}")

        return redirect(reverse_lazy("price_parser:contacts"))

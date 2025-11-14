from django.views.generic import ListView, CreateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from reportlab.platypus import Image
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from bases.models import Folios   # Ajustar ruta según tu proyecto
from .models import IngresoExtraordinario
from .forms import IngresoExtraForm,IngresoExtraFiltroForm
from django.db.models import Sum, Q




class IngresoExtraListView(LoginRequiredMixin, ListView):
    model = IngresoExtraordinario
    template_name = "finanzas/ingreso_extra_list.html"
    context_object_name = "ingresos"
    ordering = ["-fecha", "-id"]
    paginate_by = 20


class IngresoExtraCreateView(LoginRequiredMixin, CreateView):
    model = IngresoExtraordinario
    form_class = IngresoExtraForm
    template_name = "finanzas/ingreso_extra_form.html"
    success_url = reverse_lazy("finanzas:ingreso_list")

    

    def form_valid(self, form):
        ingreso = form.save(commit=False)
        ingreso.usuario = self.request.user

        # === Obtener folio desde bases_folios ===
        folio_obj = Folios.objects.get(tipo_documento="INGEX")   # definimos este tipo para ingresos extraordinarios
        ingreso.folio = folio_obj.consecutivo

        # Incrementar el folio siguiente
        folio_obj.consecutivo += 1
        folio_obj.save()

        ingreso.save()
        messages.success(self.request, f"Ingreso registrado correctamente. Folio: {ingreso.folio}")

        return super().form_valid(form)


class IngresoExtraDetailView(LoginRequiredMixin, DetailView):
    model = IngresoExtraordinario
    template_name = "finanzas/ingreso_extra_detalle.html"
    context_object_name = "ingreso"


class IngresoExtraDeleteView(LoginRequiredMixin, DeleteView):
    model = IngresoExtraordinario
    template_name = "finanzas/ingreso_extra_confirm_delete.html"
    success_url = reverse_lazy("finanzas:ingreso_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Ingreso eliminado.")
        return super().delete(request, *args, **kwargs)
    



class IngresoExtraReporteView(LoginRequiredMixin, ListView):
    model = IngresoExtraordinario
    template_name = "finanzas/ingreso_extra_reporte.html"
    context_object_name = "ingresos"

    def get_queryset(self):
        qs = IngresoExtraordinario.objects.all().order_by("-fecha")

        self.form = IngresoExtraFiltroForm(self.request.GET or None)

        if self.form.is_valid():
            fecha_inicio = self.form.cleaned_data.get("fecha_inicio")
            fecha_fin = self.form.cleaned_data.get("fecha_fin")
            proyecto = self.form.cleaned_data.get("proyecto")
            cuenta = self.form.cleaned_data.get("cuenta")
            tipo = self.form.cleaned_data.get("tipo")

            if fecha_inicio:
                qs = qs.filter(fecha__gte=fecha_inicio)

            if fecha_fin:
                qs = qs.filter(fecha__lte=fecha_fin)

            if proyecto:
                qs = qs.filter(proyecto=proyecto)

            if cuenta:
                qs = qs.filter(cuenta=cuenta)

            if tipo:
                qs = qs.filter(tipo=tipo)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ingresos = context["ingresos"]

        context["form"] = self.form

        # Totales
        context["total_general"] = ingresos.aggregate(total=Sum("monto"))["total"] or 0
        
        # Totales por tipo
        context["totales_por_tipo"] = ingresos.values("tipo").annotate(total=Sum("monto"))

        return context

from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings
from io import BytesIO
from .forms import IngresoExtraFiltroForm
from .utils import filtrar_ingresos
import os

def reporte_ingresos_pdf(request):

    form = IngresoExtraFiltroForm(request.GET)
    ingresos = filtrar_ingresos(request, form)

    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=70, bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elementos = []

    # === LOGOTIPO ===
    logo_path = os.path.join(settings.BASE_DIR, "static/base/img/inemo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=150, height=60)
        elementos.append(logo)
    else:
        elementos.append(Paragraph("<b>INEMO Constructora</b>", styles["Title"]))

    # === TÍTULO ===
    elementos.append(Paragraph("<b>Reporte de Ingresos Extraordinarios</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # === TABLA ===
    encabezados = ["Folio", "Fecha", "Estatus", "Cuenta", "Proyecto", "Tipo", "Concepto", "Referencia", "Monto"]
    data = [encabezados]

    total_general = 0

    for i in ingresos:
        data.append([
            i.folio,
            i.fecha.strftime("%d/%m/%Y"),
            "Afectado" if i.estatus == "AFECTADO" else "Pendiente",
            i.cuenta.cuenta,
            i.proyecto.nombre if i.proyecto else "—",
            i.get_tipo_display(),
            i.concepto,
            i.referencia or "—",
            f"${i.monto:,.2f}"
        ])
        total_general += i.monto

    # === TOTAL ===
    data.append(["", "", "", "", "", "", "", "TOTAL:", f"${total_general:,.2f}"])

    tabla = Table(data, colWidths=[45, 55, 65, 85, 110, 100, 200, 80, 80])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),

        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (8, 1), (8, -1), "RIGHT"),
    ]))

    elementos.append(tabla)

    pdf.build(elementos)

    response = HttpResponse(content=buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=ingresos_reporte.pdf"
    return response


from django.http import HttpResponse
from openpyxl import Workbook
from .forms import IngresoExtraFiltroForm
from .utils import filtrar_ingresos

def reporte_ingresos_excel(request):

    form = IngresoExtraFiltroForm(request.GET)
    ingresos = filtrar_ingresos(request, form)

    wb = Workbook()
    ws = wb.active
    ws.title = "Ingresos Extraordinarios"

    encabezados = [
        "Folio", "Fecha", "Estatus", "Cuenta", "Proyecto",
        "Tipo", "Concepto", "Referencia", "Monto"
    ]
    ws.append(encabezados)

    total = 0

    for i in ingresos:
        ws.append([
            i.folio,
            i.fecha.strftime("%d/%m/%Y"),
            "Afectado" if i.estatus == "AFECTADO" else "Pendiente",
            i.cuenta.nombre,
            i.proyecto.nombre if i.proyecto else "",
            i.get_tipo_display(),
            i.concepto,
            i.referencia or "",
            float(i.monto),
        ])
        total += float(i.monto)

    ws.append(["", "", "", "", "", "", "", "TOTAL", total])

    col_widths = [10, 12, 12, 20, 25, 20, 40, 20, 15]
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=ingresos_reporte.xlsx"

    wb.save(response)
    return response


from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from adm.models import Cuenta  # si la cuenta está en otro módulo, ajustar import

#@login_required(login_url="bases:login")
def afectar_ingreso_extra(request, pk):
    ingreso = get_object_or_404(IngresoExtraordinario, pk=pk)

    if ingreso.estatus == "AFECTADO":
        messages.warning(request, "Este ingreso ya fue afectado previamente.")
        return redirect("finanzas:ingreso_detalle", pk=pk)

    cuenta = ingreso.cuenta

    # Sumar monto a la cuenta asociada
    cuenta.saldo_actual += ingreso.monto
    cuenta.save()

    ingreso.estatus = "AFECTADO"
    ingreso.fecha_afectado = timezone.now()
    ingreso.save()

    messages.success(request, f"Ingreso afectado correctamente. Monto aplicado: ${ingreso.monto:,.2f}")
    return redirect("finanzas:ingreso_detalle", pk=pk)
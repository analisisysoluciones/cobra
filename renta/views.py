from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views import View
from django.shortcuts import (
    render,
    redirect, get_object_or_404
)
from .models import RentaEquipo, Cliente, TarifaEquipo, PagoRenta, RentaConcepto, ConceptoRentaCatalogo
from .forms import (RentaEquipoForm, ClienteForm, TarifaEquipoForm, RentaConceptoForm, 
                    RentaConceptoFormSet, PagoRentaForm, ConceptoRentaCatalogoForm)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.utils import timezone
from django.db.models import Sum, Q
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from io import BytesIO
from reportlab.platypus import Image
from django.conf import settings
import os
from django.http import HttpResponse
from .constants import ESTATUS_EDITABLES, TRANSICIONES_VALIDAS

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from reportlab.lib import colors

from reportlab.lib.styles import (
    getSampleStyleSheet
)

from reportlab.lib.pagesizes import letter    



CONCEPTOS_PREFIX = "conceptos"




class RentaEquipoCreateView(CreateView):
    model = RentaEquipo
    form_class = RentaEquipoForm
    template_name = "renta/renta_form.html"
    success_url = reverse_lazy("renta:renta_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["conceptos_formset"] = RentaConceptoFormSet(
                self.request.POST,
                prefix=CONCEPTOS_PREFIX,   # FIX: prefijo explícito
            )
        else:
            context["conceptos_formset"] = RentaConceptoFormSet(
                prefix=CONCEPTOS_PREFIX,   # FIX: prefijo explícito
            )
            
        context["conceptos_catalogo"] = (
            ConceptoRentaCatalogo.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        conceptos_formset = context["conceptos_formset"]

        # FIX: validar formset ANTES de guardar
        if not conceptos_formset.is_valid():
            return self.form_invalid(form)

        form.instance.calcular_importe()
        self.object = form.save()

        conceptos_formset.instance = self.object
        conceptos_formset.save()

        self.object.refresh_from_db()
        self.object.actualizar_totales()
        self.object.save()

        return redirect(self.success_url)



class RentaEquipoDetailView(DetailView):

    model = RentaEquipo

    template_name = (
        "renta/renta_detail.html"
    )

    context_object_name = "renta"




class RentaEquipoListView(ListView):
    model = RentaEquipo
    template_name = "renta/renta_list.html"
    context_object_name = "rentas"

    
        
    def get_queryset(self):

        qs = (
            super()
            .get_queryset()
            .select_related(
                "cliente",
                "equipo",
                "tarifa"
            )
        )

        q = self.request.GET.get("q")

        cliente = self.request.GET.get(
            "cliente"
        )

        estatus = self.request.GET.get(
            "estatus"
        )

        fecha_inicio = self.request.GET.get(
            "fecha_inicio"
        )

        fecha_fin = self.request.GET.get(
            "fecha_fin"
        )

        if q:

            qs = qs.filter(

                Q(folio__icontains=q) |

                Q(cliente__nombre__icontains=q) |

                Q(equipo__descripcion__icontains=q)

            )

        if cliente:

            qs = qs.filter(
                cliente_id=cliente
            )

        if estatus:

            qs = qs.filter(
                estatus=estatus
            )

        if fecha_inicio:

            qs = qs.filter(
                fecha_inicio__date__gte=fecha_inicio
            )

        if fecha_fin:

            qs = qs.filter(
                fecha_inicio__date__lte=fecha_fin
            )

        return qs.order_by("-id")
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(
            **kwargs
        )

        context["clientes"] = (
            Cliente.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        return context


def reporte_rentas(request):

    total = RentaEquipo.objects.aggregate(
        total=Sum("importe")
    )["total"] or 0

    por_cliente = RentaEquipo.objects.values("cliente__nombre")\
        .annotate(total=Sum("importe"))\
        .order_by("-total")

    return render(request, "renta/reporte_rentas.html", {
        "total": total,
        "por_cliente": por_cliente
    })        


# Estatus permitidos para editar
ESTATUS_EDITABLES = {"ACTIVA", "COTIZACION", "APROBADA"}

# Transiciones válidas por estatus actual
TRANSICIONES_VALIDAS = {
    "COTIZACION": ["COTIZACION", "APROBADA", "CANCELADA"],
    "APROBADA":   ["APROBADA", "ACTIVA", "CANCELADA"],
    "ACTIVA":     ["ACTIVA", "FINALIZADA", "CANCELADA"],
    "RENTADA":    ["RENTADA", "FINALIZADA", "CANCELADA"],
    # FINALIZADA y CANCELADA no se editan
}


class RentaEquipoUpdateView(UpdateView):
    model = RentaEquipo
    form_class = RentaEquipoForm
    template_name = "renta/renta_form.html"
    success_url = reverse_lazy("renta:renta_list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.estatus not in ESTATUS_EDITABLES:
            messages.error(request, "Esta renta no puede editarse.")
            return redirect("renta:renta_detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["conceptos_formset"] = RentaConceptoFormSet(
                self.request.POST,
                instance=self.object,
                prefix="conceptos"
            )
        else:
            context["conceptos_formset"] = RentaConceptoFormSet(
                instance=self.object,
                prefix="conceptos"
            )

        context["conceptos_catalogo"] = (
            ConceptoRentaCatalogo.objects
            .filter(activo=True)
            .order_by("nombre")
        )
        return context

    ESTATUS_EDITABLES = {"COTIZACION", "ACTIVA"}
    @transaction.atomic
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.estatus not in ESTATUS_EDITABLES:
            messages.error(request, "Este documento no puede editarse.")
            return redirect("renta:renta_detail", pk=self.object.pk)

        return super().dispatch(request, *args, **kwargs)
        
        def dispatch(self, request, *args, **kwargs):

            self.object = self.get_object()

            if self.object.estatus != "ACTIVA":

                messages.error(
                    request,
                    "La renta no puede editarse."
                )

                return redirect(
                    "renta:renta_detail",
                    pk=self.object.pk
                )

            return super().dispatch(
                request,
                *args,
                **kwargs
            )
        
    
    
class ClienteListView(ListView):
    model = Cliente
    template_name = "renta/cliente_list.html"
    context_object_name = "clientes"


class ClienteCreateView(CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "renta/cliente_form.html"
    success_url = reverse_lazy("renta:cliente_list")


class ClienteUpdateView(UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "renta/cliente_form.html"
    success_url = reverse_lazy("renta:cliente_list")            


class TarifaEquipoListView(ListView):
    model = TarifaEquipo
    template_name = "renta/tarifa_list.html"
    context_object_name = "tarifas"

    def get_queryset(self):
        return TarifaEquipo.objects.select_related("equipo").order_by("-id")

class TarifaEquipoCreateView(CreateView):
    model = TarifaEquipo
    form_class = TarifaEquipoForm
    template_name = "renta/tarifa_form.html"
    success_url = reverse_lazy("renta:tarifa_list")


class TarifaEquipoUpdateView(UpdateView):
    model = TarifaEquipo
    form_class = TarifaEquipoForm
    template_name = "renta/tarifa_form.html"
    success_url = reverse_lazy("renta:tarifa_list")







@login_required
@require_POST
def cliente_ajax_crear(request):

    nombre = request.POST.get("nombre")
    telefono = request.POST.get("telefono")

    if not nombre:

        return JsonResponse({
            "ok": False,
            "error": "Nombre requerido"
        })

    cliente = Cliente.objects.create(
        nombre=nombre,
        telefono=telefono or ""
    )

    return JsonResponse({
        "ok": True,
        "id": cliente.id,
        "nombre": cliente.nombre
    })
    
    
@login_required
def finalizar_renta(request, pk):

    renta = get_object_or_404(RentaEquipo,pk=pk)

    if renta.estatus != "ACTIVA":

        messages.warning(
            request,
            "La renta ya no puede finalizarse."
        )

        return redirect(
            "renta:renta_detail",
            pk=renta.pk
        )

    renta.actualizar_totales()

    renta.estatus = "FINALIZADA"

    renta.save()

    messages.success(
        request,
        "Renta finalizada correctamente."
    )

    return redirect(
        "renta:renta_detail",
        pk=renta.pk
    )
    
    
@login_required
def cancelar_renta(request, pk):

    renta = get_object_or_404(
        RentaEquipo,
        pk=pk
    )

    if renta.estatus == "FINALIZADA":

        messages.error(
            request,
            "Una renta finalizada no puede cancelarse."
        )

        return redirect(
            "renta:renta_detail",
            pk=renta.pk
        )

    renta.estatus = "CANCELADA"

    renta.save()

    messages.warning(
        request,
        "Renta cancelada."
    )

    return redirect(
        "renta:renta_detail",
        pk=renta.pk
    )        
    


@login_required
def renta_pdf(request, pk):

    renta = get_object_or_404(
        RentaEquipo,
        pk=pk
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=35,
        leftMargin=35,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    story = []

    # ==================================================
    # LOGO
    # ==================================================

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "base",
        "inemo_maquinaria.png"
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=140,
            height=80
        )

        logo.hAlign = "RIGHT"

        story.append(logo)

    story.append(
        Spacer(1, 10)
    )

    # ==================================================
    # TITULO
    # ==================================================

    titulo = Paragraph(

        f"""
        <para align='center'>
        <font size='18'>
        <b>RENTA DE MAQUINARIA</b>
        </font>
        <br/><br/>

        <font size='12'>
        FOLIO: <b>{renta.folio}</b>
        </font>
        </para>
        """,

        styles["BodyText"]

    )

    story.append(titulo)

    story.append(
        Spacer(1, 20)
    )

    # ==================================================
    # DATOS CLIENTE
    # ==================================================

    cliente_data = [

        [
            "CLIENTE",
            renta.cliente.nombre
        ],

        [
            "TELÉFONO",
            renta.cliente.telefono or ""
        ],

        [
            "RFC",
            renta.cliente.rfc or ""
        ],

        [
            "FECHA",
            renta.creado.strftime(
                "%d/%m/%Y %H:%M"
            )
        ],

        [
            "ESTATUS",
            renta.estatus
        ],

    ]

    tabla_cliente = Table(
        cliente_data,
        colWidths=[120, 380]
    )

    tabla_cliente.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0,0),
            (0,-1),
            colors.HexColor("#1f5f46")
        ),

        (
            "TEXTCOLOR",
            (0,0),
            (0,-1),
            colors.white
        ),

        (
            "FONTNAME",
            (0,0),
            (0,-1),
            "Helvetica-Bold"
        ),

        (
            "GRID",
            (0,0),
            (-1,-1),
            1,
            colors.grey
        ),

        (
            "BOTTOMPADDING",
            (0,0),
            (-1,-1),
            7
        ),

        (
            "FONTSIZE",
            (0,0),
            (-1,-1),
            10
        ),

    ]))

    story.append(tabla_cliente)

    story.append(
        Spacer(1, 20)
    )

    # ==================================================
    # DATOS RENTA
    # ==================================================

    datos_renta = [

        [
            "Equipo",
            renta.equipo.descripcion
        ],

        [
            "Tarifa",
            renta.tarifa.tipo_cobro
        ],

        [
            "Fecha inicio",
            renta.fecha_inicio.strftime(
                "%d/%m/%Y %H:%M"
            )
        ],

        [
            "Fecha fin",
            renta.fecha_fin.strftime(
                "%d/%m/%Y %H:%M"
            ) if renta.fecha_fin else ""
        ],

        [
            "Cantidad",
            str(renta.cantidad)
        ],

        [
            "Subtotal renta",
            f"${renta.importe}"
        ],

    ]

    tabla_renta = Table(
        datos_renta,
        colWidths=[120, 380]
    )

    tabla_renta.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0,0),
            (0,-1),
            colors.HexColor("#1f5f46")
        ),

        (
            "TEXTCOLOR",
            (0,0),
            (0,-1),
            colors.white
        ),

        (
            "FONTNAME",
            (0,0),
            (0,-1),
            "Helvetica-Bold"
        ),

        (
            "GRID",
            (0,0),
            (-1,-1),
            1,
            colors.grey
        ),

        (
            "BOTTOMPADDING",
            (0,0),
            (-1,-1),
            7
        ),

        (
            "FONTSIZE",
            (0,0),
            (-1,-1),
            10
        ),

    ]))

    story.append(tabla_renta)

    story.append(
        Spacer(1, 25)
    )

    # ==================================================
    # CONCEPTOS
    # ==================================================

    conceptos_data = [[

        "Concepto",
        "Cantidad",
        "Precio",
        "Importe"

    ]]

    for c in renta.conceptos.all():

        conceptos_data.append([

            c.concepto.nombre,

            str(c.cantidad),

            f"${c.precio}",

            f"${c.importe}"

        ])

    tabla_conceptos = Table(
        conceptos_data,
        colWidths=[220, 80, 100, 100]
    )

    tabla_conceptos.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0,0),
            (-1,0),
            colors.HexColor("#1f5f46")
        ),

        (
            "TEXTCOLOR",
            (0,0),
            (-1,0),
            colors.white
        ),

        (
            "FONTNAME",
            (0,0),
            (-1,0),
            "Helvetica-Bold"
        ),

        (
            "GRID",
            (0,0),
            (-1,-1),
            1,
            colors.grey
        ),

        (
            "ALIGN",
            (1,1),
            (-1,-1),
            "CENTER"
        ),

        (
            "BOTTOMPADDING",
            (0,0),
            (-1,-1),
            6
        ),

        (
            "FONTSIZE",
            (0,0),
            (-1,-1),
            9
        ),

    ]))

    story.append(tabla_conceptos)

    story.append(
        Spacer(1, 25)
    )

    # ==================================================
    # TOTALES
    # ==================================================

    total_data = [

        [
            "SUBTOTAL RENTA",
            f"${renta.importe}"
        ],

        [
            "SUBTOTAL CONCEPTOS",
            f"${renta.subtotal_conceptos}"
        ],

        [
            "TOTAL",
            f"${renta.total}"
        ],

    ]

    tabla_total = Table(
        total_data,
        colWidths=[350, 150]
    )

    tabla_total.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0,0),
            (-1,-1),
            colors.HexColor("#f3f4f6")
        ),

        (
            "GRID",
            (0,0),
            (-1,-1),
            1,
            colors.black
        ),

        (
            "FONTNAME",
            (0,0),
            (-1,-1),
            "Helvetica-Bold"
        ),

        (
            "FONTSIZE",
            (0,0),
            (-1,-1),
            12
        ),

        (
            "ALIGN",
            (1,0),
            (1,-1),
            "RIGHT"
        ),

        (
            "BOTTOMPADDING",
            (0,0),
            (-1,-1),
            8
        ),

        (
            "BACKGROUND",
            (0,2),
            (-1,2),
            colors.HexColor("#d1fae5")
        ),

    ]))

    story.append(tabla_total)

    story.append(
        Spacer(1, 40)
    )

    # ==================================================
    # OBSERVACIONES
    # ==================================================

    if renta.observaciones:

        obs = Paragraph(

            f"""
            <b>OBSERVACIONES:</b><br/><br/>
            {renta.observaciones}
            """,

            styles["BodyText"]

        )

        story.append(obs)

        story.append(
            Spacer(1, 30)
        )

    # ==================================================
    # FIRMAS
    # ==================================================

    firmas = Table([

        [
            "________________________",
            "________________________"
        ],

        [
            "ENTREGA",
            "RECIBE"
        ]

    ], colWidths=[250, 250])

    firmas.setStyle(TableStyle([

        (
            "ALIGN",
            (0,0),
            (-1,-1),
            "CENTER"
        ),

        (
            "FONTNAME",
            (0,1),
            (-1,1),
            "Helvetica-Bold"
        ),

        (
            "TOPPADDING",
            (0,1),
            (-1,1),
            10
        )

    ]))

    story.append(firmas)

    # ==================================================
    # BUILD PDF
    # ==================================================

    doc.build(story)

    pdf = buffer.getvalue()

    buffer.close()

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="{renta.folio}.pdf"'
    )

    response.write(pdf)

    return response


class PagoRentaCreateView(CreateView):

    model = PagoRenta

    form_class = PagoRentaForm

    template_name = (
        "renta/pago_form.html"
    )


    def dispatch(self, request, *args, **kwargs):

        self.renta = get_object_or_404(

            RentaEquipo,

            pk=self.kwargs["pk"]

        )

        if self.renta.estatus != "FINALIZADA":

            messages.error(

                request,

                "La renta debe estar FINALIZADA."

            )

            return redirect(

                "renta:renta_detail",

                pk=self.renta.pk

            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )


    def get_context_data(self, **kwargs):

        context = super().get_context_data(
            **kwargs
        )

        total_pagado = sum(
            p.importe
            for p in self.renta.pagos.all()
        )

        saldo = (
            self.renta.total -
            total_pagado
        )

        context["renta"] = self.renta

        context["total_pagado"] = total_pagado

        context["saldo"] = saldo

        return context


    def form_valid(self, form):

        importe = form.cleaned_data[
            "importe"
        ]

        ultimo_pago = (

            PagoRenta.objects

            .filter(
                renta=self.renta,
                importe=importe
            )

            .order_by("-id")

            .first()

        )

        if ultimo_pago:

            diferencia = (

                timezone.now() -
                ultimo_pago.fecha

            ).total_seconds()

            if diferencia < 10:

                messages.error(

                    self.request,

                    "Pago duplicado detectado."

                )

                return redirect(

                    "renta:renta_detail",

                    pk=self.renta.pk

                )

        form.instance.renta = (
            self.renta
        )

        form.instance.creado_por = (
            self.request.user
        )

        response = super().form_valid(
            form
        )

        self.renta.refresh_from_db()

        self.renta.actualizar_estado_financiero()

        messages.success(

            self.request,

            "Pago registrado correctamente."

        )

        return response
    
    def get_success_url(self):

        return reverse_lazy("renta:renta_detail",kwargs={"pk": self.renta.pk})
    
    
class ConceptoRentaCatalogoListView(
    LoginRequiredMixin,
    ListView
):

    model = ConceptoRentaCatalogo

    template_name = (
        "renta/catalogos/concepto_list.html"
    )

    context_object_name = (
        "conceptos"
    )


class ConceptoRentaCatalogoCreateView(
    LoginRequiredMixin,
    CreateView
):

    model = ConceptoRentaCatalogo

    form_class = (
        ConceptoRentaCatalogoForm
    )

    template_name = (
        "renta/catalogos/concepto_form.html"
    )

    success_url = reverse_lazy(
        "renta:concepto_list"
    )

    def form_valid(self, form):

        messages.success(self.request,"Concepto creado correctamente.")

        return super().form_valid(form)


class ConceptoRentaCatalogoUpdateView(
    LoginRequiredMixin,
    UpdateView
):

    model = ConceptoRentaCatalogo

    form_class = (
        ConceptoRentaCatalogoForm
    )

    template_name = (
        "renta/catalogos/concepto_form.html"
    )

    success_url = reverse_lazy(
        "renta:concepto_list"
    )

    def form_valid(self, form):

        messages.success(self.request,"Concepto actualizado correctamente.")

        return super().form_valid(form)
    
    


@login_required
def concepto_precio_ajax(request, pk):

    concepto = get_object_or_404(
        ConceptoRentaCatalogo,
        pk=pk
    )

    return JsonResponse({
        "precio": float(concepto.precio_default)
    })
    
    
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from renta.models import RentaEquipo


# views.py

class ConvertirRentaView(View):

    def get(self, request, pk):
        # Si alguien entra por GET, redirige al editor
        return redirect("renta:renta_update", pk=pk)

    def post(self, request, pk):
        renta = get_object_or_404(RentaEquipo, pk=pk)

        if renta.estatus != "COTIZACION":
            messages.error(request, "Solo se puede convertir una cotización.")
            return redirect("renta:renta_detail", pk=pk)

        renta.estatus = "ACTIVA"
        renta.save()

        messages.success(
            request,
            f"Cotización {renta.folio} convertida. Folio de renta: {renta.folio_renta}"
        )
        return redirect("renta:renta_detail", pk=pk)
    
    
    
from django.views import View
from django.http import JsonResponse
from django.template.loader import render_to_string

ESTATUS_NO_COBRABLES = {"CANCELADA", "FINALIZADA", "COTIZACION"}

class PagoRapidoView(View):

    def get(self, request, pk):
        """Devuelve el HTML del modal con datos de la renta."""
        renta = get_object_or_404(RentaEquipo, pk=pk)

        if renta.estatus in ESTATUS_NO_COBRABLES:
            return JsonResponse({"ok": False, "error": "Esta renta no puede cobrarse."})

        return JsonResponse({
            "ok": True,
            "folio": renta.folio_renta or renta.folio,
            "cliente": str(renta.cliente),
            "total": str(renta.total),
            "pagado": str(renta.total_pagado),
            "saldo": str(renta.saldo),
            "estatus_financiero": renta.estatus_financiero,
        })

    @transaction.atomic
    def post(self, request, pk):
        renta = get_object_or_404(RentaEquipo, pk=pk)

        if renta.estatus in ESTATUS_NO_COBRABLES:
            return JsonResponse({"ok": False, "error": "Esta renta no puede cobrarse."})

        form = PagoRentaForm(request.POST)

        if not form.is_valid():
            errores = {f: e.get_json_data() for f, e in form.errors.items()}
            return JsonResponse({"ok": False, "errores": errores})

        pago = form.save(commit=False)
        pago.renta = renta
        pago.save()

        # Actualiza estatus financiero
        renta.actualizar_estado_financiero()

        # Si el saldo queda en 0, finaliza automáticamente
        renta.refresh_from_db()
        if renta.estatus_financiero == "PAGADA":
            renta.estatus = "FINALIZADA"
            renta.save()

        return JsonResponse({
            "ok": True,
            "saldo_nuevo": str(renta.saldo),
            "estatus_financiero": renta.estatus_financiero,
            "estatus": renta.estatus,
            "pago_id": pago.pk,
        })


class FinalizarRentaView(View):
    """Finalización manual."""

    def post(self, request, pk):
        renta = get_object_or_404(RentaEquipo, pk=pk)

        if renta.estatus in ESTATUS_NO_COBRABLES:
            messages.error(request, "Esta renta no puede finalizarse.")
            return redirect("renta:renta_list")

        renta.estatus = "FINALIZADA"
        renta.save()
        messages.success(request, f"Renta {renta.folio_renta or renta.folio} finalizada.")
        return redirect("renta:renta_list")


class ReciboPagoView(View):
    """Genera PDF del recibo de pago."""

    def get(self, request, pago_pk):
        from django.http import HttpResponse
        import io

        pago = get_object_or_404(PagoRenta, pk=pago_pk)
        renta = pago.renta

        # Genera PDF — ver sección 3
        pdf_buffer = generar_recibo_pdf(pago, renta)

        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="recibo-{pago.pk}.pdf"'
        )
        return response    
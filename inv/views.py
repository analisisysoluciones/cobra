from django.shortcuts import render, redirect, get_object_or_404
from django.views import generic
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse_lazy
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Categoria, Material, Unidad, Requisicion, ItemRequisicion, Firma
from nomina.models import Empleado
from .forms import CategoriaForm, MaterialForm, UnidadForm, RequisicionForm, FirmaForm, ItemRequisicionForm, RequisicionFilterForm
from django.contrib.messages.views import SuccessMessageMixin
from bases.views import SinPrivilegios
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Sum
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.urls import reverse
from datetime import datetime
from django.core.files.base import ContentFile
import base64
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
import os
from django.conf import settings






# Create your views here.


class CategoriaView(LoginRequiredMixin, SinPrivilegios, generic.ListView):
    permission_required='inv.view_categoria'
    model = Categoria
    template_name="inv/categoria_list.html"
    context_object_name = "obj"
    login_url = "bases:login"

class CategoriaNew(LoginRequiredMixin, generic.CreateView):
    model = Categoria
    template_name="inv/categoria_form.html"
    context_object_name = "obj"
    form_class = CategoriaForm
    success_url = reverse_lazy("inv:categoria_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class CategoriaEdit(LoginRequiredMixin, generic.UpdateView):
    model = Categoria
    template_name="inv/categoria_form.html"
    context_object_name = "obj"
    form_class = CategoriaForm
    success_url = reverse_lazy("inv:categoria_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class CategoriaDel(LoginRequiredMixin, generic.DeleteView):
    model = Categoria
    template_name='inv/categoria_del.html'
    context_object_name='obj'
    success_url=reverse_lazy('inv:categoria_list')
    
#==========================================================================#
#==========================================================================#
#==========================================================================#


# Vistas para Unidad
class UnidadView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "inv.view_unidad"
    model = Unidad
    template_name = "inv/unidad_list.html"
    context_object_name = "unidades"
    login_url = "bases:login"

class UnidadNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Unidad
    template_name = "inv/unidad_form.html"
    context_object_name = "unidad"
    form_class = UnidadForm
    success_url = reverse_lazy("inv:unidad_list")
    login_url = "bases:login"
    success_message='Unidad capturada satifactoriamente'

    def form_valid(self, form):
        # Aquí puedes añadir lógica adicional si es necesario
        return super().form_valid(form)

class UnidadEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Unidad
    template_name = "inv/unidad_form.html"
    context_object_name = "obj"
    form_class = UnidadForm
    success_url = reverse_lazy("inv:unidad_list")
    login_url = "bases:login"
    success_message='Unidad actualizada satifactoriamente'

    def form_valid(self, form):
        # Aquí puedes añadir lógica adicional si es necesario
        return super().form_valid(form)
    
class UnidadDel(LoginRequiredMixin, generic.DeleteView):
    model = Unidad
    template_name='inv/unidad_del.html'
    context_object_name='obj'
    success_url=reverse_lazy('inv:unidad_list')
    



# Vistas para Material
class MaterialView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "inv.view_material"
    model = Material
    template_name = "inv/material_list.html"
    context_object_name = "materiales"
    login_url = "bases:login"
    

class MaterialNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Material
    template_name = "inv/material_form.html"
    context_object_name = "material"
    form_class = MaterialForm
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"
    success_message='Material capturado satifactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = Unidad.objects.all()  # Pasar todas las unidades
        return context

    def form_valid(self, form):
        form.instance.uc = self.request.user  # Asigna el usuario creador
        return super().form_valid(form)

class MaterialEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Material
    template_name = "inv/material_form.html"
    context_object_name = "obj"
    form_class = MaterialForm
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"
    success_message='Material actualizado satifactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = Unidad.objects.all()  # Pasar todas las unidades
        return context

    def form_valid(self, form):
        form.instance.um = self.request.user.id  # Asigna el usuario que modifica
        return super().form_valid(form)


class MaterialDel(LoginRequiredMixin, generic.DeleteView):
    model = Material
    template_name = "inv/material_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Eliminar Material"
        return context


def generar_reporte_materiales(request):
    materiales = Material.objects.prefetch_related('unidad_medida').all()
    
    html_string = render_to_string('inv/material_report.html', {'materiales': materiales})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_materiales.pdf"'
    
    # Convertir HTML a PDF
    pisa_status = pisa.CreatePDF(html_string, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: {}'.format(pisa_status.err))
    
    return response




@login_required(login_url='/login/')
def requisiciones(request, requisicion_id=None):
    template_name = 'inv/requisicion.html'
    materiales = Material.objects.filter(estado=True)  # Fixed: Correct import and reference to Material
    
    encabezado = None
    detalle = None
    form_enc = None

    if requisicion_id:
        encabezado = get_object_or_404(Requisicion, pk=requisicion_id)
        detalle = ItemRequisicion.objects.filter(requisicion=encabezado)

    if request.method == 'POST':
        if encabezado:
            form_enc = RequisicionForm(request.POST, instance=encabezado)
        else:
            form_enc = RequisicionForm(request.POST)
        
        form_det = ItemRequisicionForm(request.POST)

        if form_enc.is_valid():
            try:
                with transaction.atomic():
                    requisicion = form_enc.save(commit=False)
                    if not encabezado:
                        try:
                            from nomina.models import Empleado
                            empleado = Empleado.objects.get(id=request.user.id, estado=True)
                            requisicion.solicitante = empleado
                        except Empleado.DoesNotExist:
                            messages.error(request, 'El usuario no está asociado a un empleado activo.')
                            return render(request, template_name, {
                                'form_enc': form_enc,
                                'form_det': form_det,
                                'materiales': materiales,
                                'encabezado': encabezado,
                                'detalle': detalle
                            })
                    requisicion.save()

                    material_id_raw = request.POST.get('material_id')
                    cantidad_str = request.POST.get('cantidad_solicitada')
                    cantidad_entregada_str = request.POST.get('cantidad_entregada')

                    if material_id_raw or cantidad_str or cantidad_entregada_str:
                        if form_det.is_valid():
                            try:
                                material = Material.objects.get(pk=form_det.cleaned_data['material_id'])
                                cantidad = form_det.cleaned_data['cantidad_solicitada']
                                cantidad_entregada = form_det.cleaned_data.get('cantidad_entregada', 0)
                                verificado = form_det.cleaned_data.get('verificado', False)

                                if cantidad > 0:
                                    if cantidad_entregada > material.stock_actual:
                                        messages.error(request, f'No hay suficiente stock para {material.descripcion}. Stock actual: {material.stock_actual}.')
                                    else:
                                        item = ItemRequisicion(
                                            requisicion=requisicion,
                                            material=material,
                                            cantidad_solicitada=cantidad,
                                            cantidad_entregada=cantidad_entregada,
                                            verificado=verificado
                                        )
                                        item.save()
                                        messages.success(request, 'Ítem agregado correctamente.')
                                else:
                                    messages.error(request, 'La cantidad solicitada debe ser mayor a cero.')
                            except Material.DoesNotExist:
                                messages.error(request, 'Material no válido.')
                            except Exception as e:
                                messages.error(request, f'Error al guardar el ítem: {e}')
                        else:
                            messages.error(request, 'Errores en los datos del ítem. Revise los datos.')
                            print("Errores del formulario de detalle:", form_det.errors)
                    return redirect('inv:requisicion_edit', requisicion_id=requisicion.id)
            except Exception as e:
                messages.error(request, f'Error al guardar la requisición: {str(e)}')
                print(f"Error en el POST de requisiciones: {e}")
        else:
            messages.error(request, 'Errores en el formulario de la requisición. Revise los datos.')
            print("Errores del formulario de Requisicion:", form_enc.errors)
    else:
        if encabezado:
            form_enc = RequisicionForm(instance=encabezado)
        else:
            form_enc = RequisicionForm(initial={'fecha_solicitud': datetime.today()})

    contexto = {
        'materiales': materiales,
        'encabezado': encabezado,
        'detalle': detalle,
        'form_enc': form_enc,
    }

    return render(request, template_name, contexto)

@login_required(login_url='/login/')
def requisicion_list(request):
    template_name = 'inv/requisicion_list.html'
    queryset = Requisicion.objects.all()
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estatus = request.GET.get('estatus')
    if fecha_inicio and fecha_fin:
        queryset = queryset.filter(fecha_solicitud__range=[fecha_inicio, fecha_fin])
    if estatus:
        queryset = queryset.filter(estatus=estatus)
    context = {
        'obj': queryset
    }
    return render(request, template_name, context)

@login_required(login_url='/login/')
def requisicion_pdf(request, pk):
    requisicion = get_object_or_404(Requisicion, pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="requisicion_{requisicion.folio}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica", 12)
    p.drawString(100, 750, f"Inmobiliaria Inemo")
    p.drawString(100, 730, f"Requisición: {requisicion.folio}")
    p.drawString(100, 710, f"Solicitante: {requisicion.solicitante.nombre}")
    p.drawString(100, 690, f"Fecha: {requisicion.fecha_solicitud.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(100, 670, f"Estatus: {requisicion.get_estatus_display()}")
    p.drawString(100, 650, "Ítems:")

    y = 630
    for item in requisicion.items.all():
        p.drawString(120, y, f"{item.material.descripcion}: Solicitado {item.cantidad_solicitada} {item.material.unidad_medida} (Entregado: {item.cantidad_entregada})")
        y -= 20

    y -= 20
    p.drawString(100, y, "Firmas:")
    for firma in requisicion.firma_set.all():
        y -= 20
        p.drawString(120, y, f"Empleado: {firma.empleado.nombre} ({firma.fecha_firma.strftime('%d/%m/%Y %H:%M')})")
        if firma.imagen_firma:
            p.drawString(120, y - 20, "Firma digitalizada disponible")
            y -= 20

    y -= 40
    p.drawString(100, y, "Espacio para firmas físicas: _____________________________")

    p.showPage()
    p.save()
    return response

@login_required(login_url='/login/')
def subir_firma(request, requisicion_id):
    requisicion = get_object_or_404(Requisicion, pk=requisicion_id)
    if request.method == 'POST':
        form = FirmaForm(request.POST, request.FILES)
        if form.is_valid():
            firma = form.save(commit=False)
            firma.requisicion = requisicion
            firma.save()
            messages.success(request, 'Firma subida correctamente.')
            return redirect('inv:requisicion_edit', requisicion_id=requisicion.id)
        else:
            messages.error(request, 'Error al subir la firma.')
    else:
        form = FirmaForm()
    return render(request, 'inv/firma_form.html', {'form': form, 'requisicion': requisicion})

class ItemRequisicionDelete(generic.DeleteView):
    model = ItemRequisicion
    template_name = "inv/item_requisicion_del.html"
    context_object_name = 'obj'

    def get_success_url(self):
        return reverse('inv:requisicion_edit', kwargs={'requisicion_id': self.kwargs['requisicion_id']})

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        print(f"Ítem a eliminar: {self.object.material.descripcion}")
        requisicion = self.object.requisicion
        response = super().delete(request, *args, **kwargs)
        requisicion.actualizar_estado()
        return response
    
# Vista para lista
class RequisicionListView(LoginRequiredMixin, ListView):
    model = Requisicion
    template_name = 'inv/requisicion_list.html'
    context_object_name = 'requisiciones'

    def get_queryset(self):
        queryset = super().get_queryset()
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        estatus = self.request.GET.get('estatus')
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha_solicitud__range=[fecha_inicio, fecha_fin])
        if estatus:
            queryset = queryset.filter(estatus=estatus)
        return queryset

# Vista para PDF (formato de entrega)
class RequisicionPDFView(LoginRequiredMixin, DetailView):
    model = Requisicion

    def get(self, request, *args, **kwargs):
        requisicion = self.get_object()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="requisicion_{requisicion.folio}.pdf"'

        # Documento profesional
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18
        )
        story = []
        styles = getSampleStyleSheet()

        # --- LOGOTIPO ---
        logo_path = os.path.join(settings.BASE_DIR, "static", "base", "inemo.png")
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=100, height=70)
            logo.hAlign = "LEFT"
            story.append(logo)

        story.append(Paragraph("<b>INMOBILIARIA INEMO</b>", styles["Title"]))
        story.append(Paragraph("REQUISICIÓN DE MATERIALES", styles["Heading2"]))
        story.append(Spacer(1, 20))

        # --- DATOS GENERALES ---
        datos = [
            ["Folio:", str(requisicion.folio)],
            ["Solicitante:", str(requisicion.solicitante)],
            ["Proyecto:", str(requisicion.proyecto) if requisicion.proyecto else "---"],  # 🔹 agregado aquí
            ["Fecha Solicitud:", requisicion.fecha_solicitud.strftime("%d/%m/%Y %H:%M")],
            ["Estatus:", requisicion.get_estatus_display()],
        ]
        tabla_datos = Table(datos, colWidths=[120, 400])
        tabla_datos.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ]))
        story.append(tabla_datos)
        story.append(Spacer(1, 20))

        # --- TABLA DE MATERIALES ---
        items = [["Clave", "Descripción", "Cant. Solicitada", "Cant. Entregada"]]
        for item in requisicion.items.all():
            items.append([
                item.material.clave,
                item.material.descripcion,
                f"{item.cantidad_solicitada:.3f}",  # siempre 3 decimales
                f"{item.cantidad_entregada:.3f}",
            ])

        tabla_items = Table(items, colWidths=[80, 250, 100, 100])

        # Estilo base de la tabla
        estilo = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),  # encabezado gris
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ])

        # Agregar color intercalado a filas de datos
        for i in range(1, len(items)):  # desde la segunda fila (los datos)
            if i % 2 == 0:
                estilo.add("BACKGROUND", (0, i), (-1, i), colors.whitesmoke)

        tabla_items.setStyle(estilo)

        story.append(Paragraph("<b>Materiales Solicitados</b>", styles["Heading3"]))
        story.append(tabla_items)
        story.append(Spacer(1, 30))

        # --- FIRMAS ---
        story.append(Paragraph("<b>Firmas</b>", styles["Heading3"]))
        story.append(Spacer(1, 40))

        firmas = [
            ["__________________________", "__________________________"],
            ["Solicitante", "Responsable de Almacén"]
        ]
        tabla_firmas = Table(firmas, colWidths=[250, 250])
        tabla_firmas.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(tabla_firmas)

        # Construir documento
        doc.build(story)
        return response


@require_POST
def requisiciones_add_detalle_view(request, requisicion_id):
    requisicion = get_object_or_404(Requisicion, pk=requisicion_id)

    try:
        material_id = request.POST.get("material_id")
        cantidad_solicitada = int(request.POST.get("cantidad_solicitada", 0))
        cantidad_entregada = int(request.POST.get("cantidad_entregada", 0))

        if not material_id or cantidad_solicitada <= 0:
            return JsonResponse({"success": False, "errors": "Datos inválidos"})

        material = get_object_or_404(Material, pk=material_id)
     

        item = ItemRequisicion.objects.create(
            requisicion=requisicion,
            material=material,
            cantidad_solicitada=cantidad_solicitada,
            cantidad_entregada=cantidad_entregada,
        )


        # Recalcular totales de la requisición
        requisicion.calcular_totales()

        return JsonResponse({
            "success": True,
            "message": "Detalle agregado correctamente",
            "requisicion_id": requisicion.id,
            "item": {
                "id": item.id,
                "material_clave": material.clave,
                "material_descripcion": material.descripcion,
                "cantidad_solicitada": item.cantidad_solicitada,
                "cantidad_entregada": item.cantidad_entregada,
            },
            "new_total": requisicion.total_solicitada,
        })

    except Exception as e:
        return JsonResponse({"success": False, "errors": str(e)})
    



def requisicion_entregar(request, requisicion_id):
    requisicion = get_object_or_404(Requisicion, pk=requisicion_id)

    if request.method == "POST":
        for item in requisicion.items.all():
            entregada_str = request.POST.get(f"entregada_{item.id}", "0")
            try:
                cantidad_entregada = int(entregada_str)
                if cantidad_entregada < 0:
                    cantidad_entregada = 0
                item.cantidad_entregada = cantidad_entregada
                item.save()
            except ValueError:
                pass

        # Verificar si todos los items fueron entregados
        if all(item.cantidad_entregada >= item.cantidad_solicitada for item in requisicion.items.all()):
            requisicion.estatus = "ENTREGADA"
            requisicion.save()

        messages.success(request, "Entrega registrada correctamente.")
        return redirect(reverse("inv:requisicion_list"))

    contexto = {
        "requisicion": requisicion,
        "items": requisicion.items.all()
    }
    return render(request, "inv/requisicion_entregar.html", contexto)



def reporte_requisiciones(request):
    form = RequisicionFilterForm(request.GET or None)
    requisiciones = Requisicion.objects.all()

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        estatus = form.cleaned_data.get('estatus')
        solicitante = form.cleaned_data.get('solicitante')

        if fecha_inicio:
            requisiciones = requisiciones.filter(fecha_solicitud__date__gte=fecha_inicio)
        if fecha_fin:
            requisiciones = requisiciones.filter(fecha_solicitud__date__lte=fecha_fin)
        if estatus:
            requisiciones = requisiciones.filter(estatus=estatus)
        if solicitante:
            requisiciones = requisiciones.filter(solicitante=solicitante)

    return render(request, "inv/reporte_requisiciones.html", {
        "form": form,
        "requisiciones": requisiciones
    })



def reporte_requisiciones_pdf(request):
    form = RequisicionFilterForm(request.GET or None)
    requisiciones = Requisicion.objects.all()

    # aplicar filtros
    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        estatus = form.cleaned_data.get('estatus')
        solicitante = form.cleaned_data.get('solicitante')

        if fecha_inicio:
            requisiciones = requisiciones.filter(fecha_solicitud__date__gte=fecha_inicio)
        if fecha_fin:
            requisiciones = requisiciones.filter(fecha_solicitud__date__lte=fecha_fin)
        if estatus:
            requisiciones = requisiciones.filter(estatus=estatus)
        if solicitante:
            requisiciones = requisiciones.filter(solicitante=solicitante)

    # respuesta HTTP PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_requisiciones.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # estilos personalizados
    title_style = ParagraphStyle(
        'TitleLeft',
        parent=styles['Title'],
        alignment=0,  # LEFT
    )
    detail_style = ParagraphStyle(
        'Detail',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        alignment=0,  # LEFT
    )
    header_style = ParagraphStyle(
        'HeaderSmall',
        parent=styles['Heading4'],
        alignment=0,  # LEFT
    )

    # logotipo
    logo_path = os.path.join(settings.BASE_DIR, "static", "base", "inemo.jpg")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=110, height=78)
        story.append(logo)
    story.append(Spacer(1, 12))

    # título
    story.append(Paragraph("Reporte de Requisiciones", title_style))
    story.append(Spacer(1, 8))

    # encabezados de tabla
    data = [[Paragraph("<b>Folio</b>", header_style),
             Paragraph("<b>Detalle</b>", header_style)]]

    for r in requisiciones:
        folio_str = str(r.folio)
        folio_show = folio_str if len(folio_str) <= 18 else f"{folio_str[:18]}…"

        # 🔹 usar __str__ de Proyecto
        proyecto_nombre = str(r.proyecto) if r.proyecto else "---"

        # fila 1 → folio
        data.append([folio_show, ""])

        # fila 2 → detalles
        detalle_par = Paragraph(
            f"Fecha: {r.fecha_solicitud.strftime('%d/%m/%Y')}<br/>"
            f"Estatus: {r.get_estatus_display()}<br/>"
            f"Solicitante: {r.solicitante}<br/>"
            f"Proyecto: {proyecto_nombre}",
            detail_style
        )
        data.append(["", detalle_par])

    # anchos de columnas
    tabla = Table(data, colWidths=[120, 420])

    estilo = TableStyle([
        # encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),

        # cuerpo
        ("ALIGN", (0, 1), (-1, -1), "LEFT"),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),

        # paddings
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),

        # rejilla
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ])

    # alternar color cada bloque de 2 filas
    row = 1
    while row < len(data):
        estilo.add("BACKGROUND", (0, row), (-1, row + 1), colors.whitesmoke)
        row += 2

    tabla.setStyle(estilo)
    story.append(tabla)

    story.append(Spacer(1, 16))
    story.append(Paragraph(f"Total requisiciones: {requisiciones.count()}", styles["Normal"]))

    doc.build(story)
    return response

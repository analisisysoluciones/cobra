from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import FormView
from django.views import generic
from django.templatetags.static import static
from django.db.models.functions import Coalesce

import openpyxl
import tempfile

from django.http import JsonResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import(Proveedor, CompraEnc, CompraDet)
from adm.models import(Proyecto, TipoDocumento, Cuenta)

from inv.models import Material
#from .calculos import calcular_nomina_semanal_todos

from .forms import( ProveedorForm, CompraEncForm, CompraDetForm, FiltroCompraForm,  FiltroCompraMatForm )


from xhtml2pdf import pisa
from django.http import HttpResponse
from django.template.loader import render_to_string, get_template
from django.contrib import messages
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Max, F, ExpressionWrapper, DecimalField, Avg
from django.contrib.messages.views import SuccessMessageMixin
import uuid
from django.utils.timezone import now
from io import BytesIO
from django.http import FileResponse
from datetime import timedelta, datetime, date
from io import BytesIO
from decimal import Decimal
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader
import os
from django.conf import settings
import locale
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.utils.formats import number_format
from django.views.decorators.http import require_POST









#ffont_path = os.path.join(settings.BASE_DIR, "static/fonts/Arial.ttf")
#pdfmetrics.registerFont(TTFont("Arial", font_path))


# Establecer idioma español para los nombres de los meses
#locale.setlocale(locale.LC_TIME, "es_ES.utf8")



# Lista de proveedores
class ProveedorListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "cxp.view_proveedor"
    model = Proveedor
    template_name = 'cxp/proveedor_list.html'  # Debes crear este archivo HTML
    context_object_name = 'proveedores'
    login_url = "bases:login"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        print(queryset)  # Verifica qué se está pasando
        return queryset
    
    

# Crear proveedor
class ProveedorCreateView(LoginRequiredMixin, generic.CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'cxp/proveedor_form.html'  # Debes crear este archivo HTML
    success_url = reverse_lazy('cxp:proveedor_list')  # Ajusta la URL según sea necesario
    login_url = "bases:login"
    
    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)

# Actualizar proveedor
class ProveedorUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'cxp/proveedor_form.html'
    success_url = reverse_lazy('cxp:proveedor_list')
    login_url = "bases:login"
    
    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

# Eliminar proveedor
class ProveedorDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Proveedor
    template_name = 'cxp/proveedor_del.html'  # Debes crear este archivo HTML
    context_object_name='obj'
    success_url = reverse_lazy('cxp:proveedor_list')
    login_url = "bases:login"




#---------------------------------------------------------------------------------------------#
# Vistas para los documentos
#
#---------------------------------------------------------------------------------------------#


class ComprasView(LoginRequiredMixin, generic.ListView):
    model = CompraEnc
    template_name = 'cxp/compras_list.html'
    context_object_name = 'obj'  # Asegura que en el template se use 'obj'

    def get_queryset(self):
        compras = super().get_queryset()
        hoy = timezone.now().date()
        
        for compra in compras:
            if compra.fecha_pago:
                dias_restantes = (compra.fecha_pago - hoy).days
                if dias_restantes < 0:
                    compra.semaforo = "red"
                elif dias_restantes == 0:
                    compra.semaforo = "red"
                elif dias_restantes <= 3:
                    compra.semaforo = "yellow"
                else:
                    compra.semaforo = "green"
            else:
                compra.semaforo = "gray"  # Si no tiene fecha de pago
        return compras
    
    # Este form_valid aquí es para una clase basada en vista, no para la función 'compras' de abajo
    # Lo he dejado porque estaba en tu código original, pero no se usa con la función 'compras'
    def form_valid(self, form):
        # Calculas el importe antes de guardar
        compra_detalle = form.save(commit=False)
        compra_detalle.importe = compra_detalle.cantidad * compra_detalle.precio_unitario
        compra_detalle.save()
        return super().form_valid(form)
  
  
@login_required(login_url='/login/')
#@permission_required('cmp.view_comprasb',login_url='bases:sin_privilegios')

def compras(request, compra_id=None):
    template_name = 'cxp/comprax.html'
    materialx = Material.objects.filter(estado=True) # Para la tabla de selección de materiales
    
    encabezado = None
    detalle = None
    form_enc = None # Se inicializa para que siempre esté definido

    if compra_id:
        encabezado = get_object_or_404(CompraEnc, pk=compra_id)
        # Asegúrate de que related_name de CompraEnc a CompraDet sea 'documentos_d'
        detalle = CompraDet.objects.filter(compra=encabezado)

    if request.method == 'POST':
        # Instancia del formulario de encabezado
        if encabezado:
            form_enc = CompraEncForm(request.POST, request.FILES, instance=encabezado)
        else:
            form_enc = CompraEncForm(request.POST, request.FILES)
        
        # Instancia del formulario de detalle para la parte de agregar material
        form_det = CompraDetForm(request.POST)

        if form_enc.is_valid():
            try:
                with transaction.atomic():
                    compra_enc = form_enc.save(commit=False)
                    if not encabezado: # Solo al crear la primera vez
                        compra_enc.uc = request.user
                    else:
                        compra_enc.um = request.user.id
                    
                    compra_enc.save() # Guarda el encabezado de la compra

                    # Si el encabezado se guardó o actualizó correctamente,
                    # intentamos procesar el detalle si los campos relevantes no están vacíos
                    # Los valores vienen del request.POST, no del form_det.cleaned_data inicialmente
                    material_id_raw = request.POST.get('material_id') # Usar el name correcto del input
                    cantidad_str = request.POST.get('cantidad') # Asegúrate que el name en HTML es 'cantidad'
                    precio_unitario_str = request.POST.get('precio_unitario') # Asegúrate que el name en HTML es 'precio_unitario'


                    # Verificar si hay datos de detalle para procesar (es decir, el usuario intentó agregar uno)
                    # Lo evaluamos basándonos en los datos brutos del POST para decidir si el form_det debe validarse
                    if material_id_raw or cantidad_str or precio_unitario_str:
                        # Si hay algún dato para el detalle, validamos form_det
                        if form_det.is_valid(): 
                            try:
                                # material_id ahora viene de form_det.cleaned_data, ya es int
                                material = Material.objects.get(pk=form_det.cleaned_data['material_id']) 
                                cantidad = form_det.cleaned_data['cantidad']
                                precio_unitario = form_det.cleaned_data['precio_unitario']

                                if cantidad > 0 and precio_unitario > 0:
                                    det_obj = CompraDet(
                                        compra = compra_enc, # Usa la instancia recién guardada
                                        material = material,
                                        cantidad = cantidad,
                                        precio_unitario = precio_unitario,
                                        uc = request.user
                                    )
                                    det_obj.save() # El save() del modelo CompraDet calcula el importe y actualiza CompraEnc.total
                                    messages.success(request, 'Detalle agregado correctamente.')
                                else:
                                    messages.error(request, 'La cantidad y el precio unitario del detalle deben ser mayores a cero.')
                            except Material.DoesNotExist:
                                messages.error(request, 'El material seleccionado para el detalle no es válido.')
                            except Exception as e:
                                messages.error(request, f'Error al guardar el detalle: {e}')
                        else:
                            # Si el form_det no es válido (ej. campos vacíos o tipo incorrecto)
                            print("Errores del formulario de detalle:", form_det.errors)
                            messages.error(request, 'Hubo errores en los datos del detalle. Por favor, revise los datos del material, cantidad y precio unitario.')
                    
                    # Redirige a la página de edición de la compra recién creada/actualizada
                    return redirect('cxp:compras_edit', compra_id=compra_enc.pk)

            except Exception as e:
                # Captura cualquier error que ocurra durante la transacción o el guardado del encabezado
                messages.error(request, f'Error al guardar la compra: {e}')
                print(f"Error en el POST de compras (encabezado): {e}")
        else:
            # Si el formulario del encabezado no es válido
            print("Errores del formulario de CompraEnc:", form_enc.errors)
            messages.error(request, 'Hubo errores en el formulario de la compra. Por favor, revise los datos del encabezado.')
            # Los errores de form_enc se pasarán al contexto automáticamente
    
    else: # GET request
        if encabezado:
            form_enc = CompraEncForm(instance=encabezado)
        else:
            form_enc = CompraEncForm(initial={'fecha': date.today()}) # Para precargar la fecha actual
    
    # Asegúrate de que 'form_enc' y 'detalle' siempre estén en el contexto
    contexto = {
        'materiales': materialx,
        'encabezado': encabezado,
        'detalle': detalle,
        'form_enc': form_enc,
    }
    
    return render(request, template_name, contexto)


class CompraDetDelete(LoginRequiredMixin, generic.DeleteView):
    model = CompraDet
    template_name = "cxp/compras_det_del.html"
    context_object_name = 'obj'

    def get_success_url(self):
        return reverse('cxp:compras_edit', kwargs={'compra_id': self.kwargs['compra_id']})

    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        print(f"Producto a eliminar: {self.object.material.descripcion}") # Cambiado de producto.nombre a material.descripcion
        compra = self.object.compra
        response = super().delete(request, *args, **kwargs)

        # Actualizar el total de la compra
        # Usar related_name 'documentos_d' que definiste en CompraEnc
        total = compra.documentos_d.aggregate(total=Sum('importe'))['total'] or 0
        compra.total = total
        compra.save()

        return response




def imprime_compra(request, compra_id):
    # Obtener la compra y sus detalles
    compra = CompraEnc.objects.prefetch_related("encabezado").get(id=compra_id)
    detalles = compra.encabezado.all()

    # Calcular el total de la compra sumando los importes de los detalles
    total_compra = sum(detalle.importe for detalle in detalles)

    # Pasar los valores al contexto
    template_path = "cxp/reporte_compra.html"
    context = {
        "compra": compra,
        "detalles": detalles,
        "total_compra": total_compra,  # Se agrega el total calculado
    }

    # Renderizar el template HTML con los datos
    template = get_template(template_path)
    html = template.render(context)

    # Configurar la respuesta como un PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=compra_{compra.folio_documento}.pdf"

    # Generar el PDF
    pisa_status = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=response)

    if pisa_status.err:
        return HttpResponse("Error al generar el PDF", content_type="text/plain")

    return response




# Subir Archivo Principal
def subir_archivo_pdf(request, compra_id):
    compra = get_object_or_404(CompraEnc, pk=compra_id)
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_pdf')
        if archivo:
            compra.archivo_pdf = archivo
            compra.save()
            messages.success(request, 'Archivo principal subido correctamente.')
            return redirect(reverse('cxp:compras_list'))
    return render(request, 'compras/subir_archivo_pdf.html', {'compra': compra})

# Subir Evidencia Recoge
def subir_evidencia_recoge(request, compra_id):
    compra = get_object_or_404(CompraEnc, pk=compra_id)
    if request.method == 'POST':
        evidencia = request.FILES.get('evidencia_recoge')
        if evidencia:
            compra.evidencia_recoge = evidencia
            compra.save()
            messages.success(request, 'Evidencia de recogido subida correctamente.')
            return redirect(reverse('cxp:compras_list'))
    return render(request, 'compras/subir_evidencia_recoge.html', {'compra': compra})

# Subir Evidencia Uso
def subir_evidencia_uso(request, compra_id):
    compra = get_object_or_404(CompraEnc, pk=compra_id)
    if request.method == 'POST':
        evidencia = request.FILES.get('evidencia_uso')
        if evidencia:
            compra.evidencia_uso = evidencia
            compra.save()
            messages.success(request, 'Evidencia de uso subida correctamente.')
            return redirect(reverse('cxp:compras_list'))
    return render(request, 'compras/subir_evidencia_uso.html', {'compra': compra})


def subir_todos_los_archivos(request, compra_id):
    compra = get_object_or_404(CompraEnc, pk=compra_id)
    if request.method == 'POST':
        archivo_pdf = request.FILES.get('archivo_pdf')
        evidencia_recoge = request.FILES.get('evidencia_recoge')
        evidencia_uso = request.FILES.get('evidencia_uso')

        if archivo_pdf:
            compra.archivo_pdf = archivo_pdf
        if evidencia_recoge:
            compra.evidencia_recoge = evidencia_recoge
        if evidencia_uso:
            compra.evidencia_uso = evidencia_uso

        compra.save()
        messages.success(request, 'Archivos subidos correctamente.')
        return redirect('cxp:compras_list')

    return render(request, 'cxp/subir_todos_archivos.html', {'compra': compra})


@require_POST
def compras_add_detalle_view(request, compra_id):
    try:
        encabezado = get_object_or_404(CompraEnc, pk=compra_id)

        material_id = request.POST.get('material_id')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario')

        print(f"DEBUG: compra_id recibido: {compra_id}")
        print(f"DEBUG: material_id recibido: {material_id}")
        print(f"DEBUG: cantidad recibido: {cantidad}")
        print(f"DEBUG: precio_unitario recibido: {precio_unitario}")

        if not material_id or not cantidad or not precio_unitario:
            print("DEBUG: Falta algún campo requerido.")
            return JsonResponse({'success': False, 'errors': 'Todos los campos (material, cantidad, precio) son requeridos.'}, status=400)

        material = Material.objects.get(pk=material_id)
        cantidad = float(cantidad)
        precio_unitario = float(precio_unitario)
        importe = cantidad * precio_unitario

        print(f"DEBUG: Material encontrado: {material}")
        print(f"DEBUG: Cantidad convertida: {cantidad}")
        print(f"DEBUG: Precio unitario convertido: {precio_unitario}")
        print(f"DEBUG: Importe calculado: {importe}")

        # === CAMBIO CRÍTICO AQUÍ: Agrega el usuario creador ===
        # Asumiendo que 'uc' es el campo en CompraDet para el usuario creador.
        # Si tu campo se llama diferente (ej. 'usuario_creador', 'creado_por'), cámbialo.
        # Asegúrate de que request.user es un usuario autenticado (has iniciado sesión).
        if request.user.is_authenticated:
            usuario_creador = request.user
        else:
            # Manejar el caso de usuario no autenticado si esto no debería suceder
            # Podrías redirigir al login o devolver un error
            print("DEBUG: Usuario no autenticado. No se puede crear detalle sin uc_id.")
            return JsonResponse({'success': False, 'errors': 'Usuario no autenticado para crear detalle.'}, status=401)


        detalle = CompraDet.objects.create(
            compra=encabezado,
            material=material,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            importe=importe,
            uc=usuario_creador, # <-- ¡AQUÍ ESTÁ EL CAMBIO!
            # Si tienes otros campos 'null=False' en CompraDet, agrégalos aquí también.
            # Por ejemplo, si también hay un 'um_id' (unidad de medida) que no acepta nulos:
            # um=material.unidad_medida, # Asumiendo que Material tiene una unidad de medida
        )
        
        print(f"DEBUG: Detalle de compra creado: {detalle.pk}")

        encabezado.total = encabezado.documentos_d.aggregate(sum_importe=Sum('importe'))['sum_importe'] or Decimal('0.00')
        encabezado.save()
        new_total = encabezado.total
        
        print(f"DEBUG: Total del encabezado actualizado: {new_total}")

        response_data = {
            'success': True,
            'message': 'Detalle añadido correctamente!',
            'item': {
                'id': detalle.pk,
                'material_clave': material.clave,
                'material_descripcion': material.descripcion,
                'cantidad': f'{detalle.cantidad:.3f}',
                'precio_unitario': f'{detalle.precio_unitario:.2f}',
                'importe': f'{detalle.importe:.2f}',
            },
            'compra_id': encabezado.pk,
            'new_total': f'{new_total:.2f}'
        }
        return JsonResponse(response_data)

    except Material.DoesNotExist:
        print(f"DEBUG: Material con ID {material_id} no existe.")
        return JsonResponse({'success': False, 'errors': 'El material seleccionado no existe.'}, status=400)
    except ValueError as e:
        print(f"DEBUG: Error de valor al convertir cantidad/precio: {e}")
        return JsonResponse({'success': False, 'errors': 'Cantidad o precio no válidos. Asegúrese de que sean números.'}, status=400)
    except Exception as e:
        print(f"DEBUG: Ocurrió un error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'errors': f'Ocurrió un error inesperado en el servidor: {str(e)}'}, status=500)
    

# views.py



# views.py


def reporte_compras(request):
    form = FiltroCompraForm(request.GET or None)
    #compras = CompraEnc.objects.all()
    compras = CompraEnc.objects.all().prefetch_related('documentos_d')

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        proveedor = form.cleaned_data.get('proveedor')
        estatus_pago = form.cleaned_data.get('estatus_pago')
        proyecto = form.cleaned_data.get('proyecto')

        if fecha_inicio:
            compras = compras.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            compras = compras.filter(fecha__lte=fecha_fin)
        if proveedor:
            compras = compras.filter(proveedor=proveedor)
        if estatus_pago:
            compras = compras.filter(estatus_pago=estatus_pago)
        if proyecto:
            compras = compras.filter(proyecto=proyecto)

    compras = compras.annotate(
        pagos_realizados=Sum('pagos__monto')
    ).annotate(
        saldo_pendiente=ExpressionWrapper(
            F('total') - (F('pagos_realizados') or 0),
            output_field=DecimalField()
        )
    )

    # Totales
    total_compras = compras.aggregate(total=Sum('total'))['total'] or 0
    total_pagado = compras.aggregate(pagado=Sum('pagos_realizados'))['pagado'] or 0
    total_saldo = total_compras - total_pagado
    total_registros = compras.count()

    # --- EXPORTACIONES ---
    export_format = request.GET.get('export')

    if export_format == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte de Compras"

        headers = ['Fecha', 'Proveedor', 'Folio', 'Total', 'Pagado', 'Saldo', 'Estado', 'Estatus Pago']
        ws.append(headers)

        for c in compras:
            ws.append([
                c.fecha.strftime('%Y-%m-%d'),
                str(c.proveedor),
                c.folio_documento,
                float(c.total),
                float(c.pagos_realizados or 0),
                float(c.saldo_pendiente or 0),
                c.estado,
                c.estatus_pago,
            ])

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=reporte_compras.xlsx'
        wb.save(response)
        return response

    elif export_format == 'pdf':
        template_path = 'cxp/reporte_compras_pdf.html'
        context = {
            'compras': compras,
            'total_compras': total_compras,
            'total_pagado': total_pagado,
            'total_saldo': total_saldo,
            'total_registros': total_registros,
        }

        template = get_template(template_path)
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_compras.pdf"'

        pisa_status = pisa.CreatePDF(BytesIO(html.encode('UTF-8')), dest=response, encoding='UTF-8')

        if pisa_status.err:
            return HttpResponse('Error al generar PDF', status=500)
        return response
    
        # ✅ Este bloque evita que la vista no retorne nada
    context = {
        'form': form,
        'compras': compras,
        'total_compras': total_compras,
        'total_pagado': total_pagado,
        'total_saldo': total_saldo,
        'total_registros': total_registros,
    }
    return render(request, 'cxp/reporte_compras.html', context)



# ====================================================================
# VISTA PRINCIPAL DEL REPORTE DE COMPRAS POR MATERIALES
# ====================================================================
def reporte_compras_materiales(request):
    # 1. Instanciar el formulario de filtro con los datos de la solicitud GET
    form = FiltroCompraMatForm(request.GET) # Usamos el formulario de filtro consolidado


    # --- AÑADE ESTAS LÍNEAS JUSTO AQUÍ, SI NO LAS HAS AÑADIDO O LAS QUITASTE ---
    print("\n--- INICIO DEPURACIÓN PROVEEDOR EN VIEWS.PY ---")
    if 'proveedor' in form.fields:
        print(f"El campo 'proveedor' EXISTE en el formulario.")
        queryset_proveedor = form.fields['proveedor'].queryset
        print(f"Tipo de queryset: {type(queryset_proveedor)}")
        print(f"El queryset del campo 'proveedor' tiene {queryset_proveedor.count()} elementos.")
        if queryset_proveedor.exists():
            print("Primeros 5 proveedores en el queryset:")
            for p in queryset_proveedor[:5]:
                # Asegúrate de que 'razon_social' sea el campo correcto para mostrar
                print(f"  - ID: {p.id}, Razón Social: {p.razon_social}")
        else:
            print("¡ADVERTENCIA! El queryset del campo 'proveedor' está VACÍO.")
    else:
        print("¡ERROR GRAVE! El campo 'proveedor' NO se encontró en el formulario 'FiltroCompraMatForm'.")
    print("--- FIN DEPURACIÓN PROVEEDOR EN VIEWS.PY ---\n")
    # --- FIN DEPURACIÓN ---

    detalles = CompraDet.objects.select_related('material', 'compra', 'compra__proveedor')
    resumen = [] # Inicializa resumen, se llenará si el formulario es válido

    # 2. Aplicar filtros si el formulario es válido
    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        proveedor_obj = form.cleaned_data.get('proveedor') # Esto será un objeto Proveedor o None
        estatus_pago = form.cleaned_data.get('estatus_pago')
        proyecto_obj = form.cleaned_data.get('proyecto') # Esto será un objeto Proyecto o None

        if fecha_inicio:
            detalles = detalles.filter(compra__fecha__gte=fecha_inicio)
        if fecha_fin:
            detalles = detalles.filter(compra__fecha__lte=fecha_fin)
        if proveedor_obj: # Si se seleccionó un proveedor específico
            detalles = detalles.filter(compra__proveedor=proveedor_obj)
        if estatus_pago:
            detalles = detalles.filter(compra__estatus_pago=estatus_pago)
        if proyecto_obj:
            detalles = detalles.filter(compra__proyecto=proyecto_obj)


        # 3. Calcular el resumen basado en los detalles filtrados
        resumen = detalles.values(
            'material__id',
            'material__descripcion'
        ).annotate(
            cantidad_total=Sum('cantidad', output_field=DecimalField()),
            importe_total=Sum('importe', output_field=DecimalField()),
            precio_promedio=ExpressionWrapper(
                Sum('importe', output_field=DecimalField()) / Sum('cantidad', output_field=DecimalField()),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).order_by('material__descripcion')

    # 4. Renderizar la plantilla pasando el formulario y el resumen
    return render(request, 'cxp/reporte_materiales.html', {
        'resumen': resumen,
        'form': form, # ¡Aquí está la clave! Pasamos la instancia del formulario
    })

# ====================================================================
# VISTAS DE EXPORTACIÓN (AJUSTADAS PARA USAR EL MISMO FORMULARIO)
# ====================================================================

def exportar_excel_materiales(request):
    # Usamos el mismo formulario de filtro para la exportación
    form = FiltroCompraMatForm(request.GET or None)
    detalles = CompraDet.objects.select_related('material', 'compra', 'compra__proveedor')

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        proveedor_obj = form.cleaned_data.get('proveedor')
        estatus_pago = form.cleaned_data.get('estatus_pago')
        proyecto_obj = form.cleaned_data.get('proyecto')

        if fecha_inicio:
            detalles = detalles.filter(compra__fecha__gte=fecha_inicio)
        if fecha_fin:
            detalles = detalles.filter(compra__fecha__lte=fecha_fin)
        if proveedor_obj:
            detalles = detalles.filter(compra__proveedor=proveedor_obj)
        if estatus_pago:
            detalles = detalles.filter(compra__estatus_pago=estatus_pago)
        if proyecto_obj:
            detalles = detalles.filter(compra__proyecto=proyecto_obj)

    resumen = detalles.values(
        'material__id',
        'material__descripcion'
    ).annotate(
        cantidad_total=Sum('cantidad', output_field=DecimalField()),
        importe_total=Sum('importe', output_field=DecimalField())
    ).order_by('material__descripcion')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Materiales"

    ws.append(["Material", "Cantidad Total", "Importe Total"])
    for row in resumen:
        ws.append([
            row["material__descripcion"],
            float(row["cantidad_total"] or 0),
            float(row["importe_total"] or 0),
        ])

    response = HttpResponse(content_type="application/ms-excel")
    response["Content-Disposition"] = 'attachment; filename="reporte_materiales.xlsx"'
    wb.save(response)
    return response

def exportar_pdf_materiales(request):
    # Usamos el mismo formulario de filtro para la exportación
    form = FiltroCompraMatForm(request.GET or None)
    detalles = CompraDet.objects.select_related('material', 'compra', 'compra__proveedor', 'compra__proyecto')

    nombre_proyecto = None
    fecha_inicio_str = None # Para la cadena de texto en el PDF
    fecha_fin_str = None    # Para la cadena de texto en el PDF
    proveedor_nombres = []

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        proveedor_obj = form.cleaned_data.get('proveedor')
        estatus_pago = form.cleaned_data.get('estatus_pago')
        proyecto_obj = form.cleaned_data.get('proyecto')

        if fecha_inicio:
            detalles = detalles.filter(compra__fecha__gte=fecha_inicio)
            fecha_inicio_str = fecha_inicio.strftime('%d/%m/%Y')
        if fecha_fin:
            detalles = detalles.filter(compra__fecha__lte=fecha_fin)
            fecha_fin_str = fecha_fin.strftime('%d/%m/%Y')
        
        if proveedor_obj: # Si se seleccionó un único proveedor
            detalles = detalles.filter(compra__proveedor=proveedor_obj)
            proveedor_nombres = [proveedor_obj.razon_social] # Asumiendo que 'nombre' es el campo de nombre del proveedor
        
        if estatus_pago:
            detalles = detalles.filter(compra__estatus_pago=estatus_pago)
        
        if proyecto_obj: # Si se seleccionó un proyecto en el formulario
            detalles = detalles.filter(compra__proyecto=proyecto_obj)
            nombre_proyecto = proyecto_obj.nombre # Asumiendo que 'nombre' es el campo de nombre del proyecto
        else: # Si no se seleccionó un proyecto en el filtro, pero quieres mostrar si todos los resultados tienen el mismo
            proyectos_en_resultados = detalles.values_list('compra__proyecto__nombre', flat=True).distinct()
            if len(proyectos_en_resultados) == 1:
                nombre_proyecto = proyectos_en_resultados[0]


        resumen = detalles.values(
            'material__id',
            'material__descripcion'
        ).annotate(
            cantidad_total=Sum('cantidad', output_field=DecimalField()),
            importe_total=Sum('importe', output_field=DecimalField())
        ).order_by('material__descripcion')
    else:
        # Si el formulario no es válido al exportar PDF (ej. al cargar sin filtros),
        # puedes inicializar resumen como vacío o con todos los datos sin filtrar.
        resumen = [] # Opcional: si quieres un PDF vacío o con todos los datos al no haber filtros válidos

    template = get_template("cxp/pdf_reporte_materiales.html")
    html = template.render({
        'resumen': resumen,
        'fecha_impresion': now().strftime('%d/%m/%Y %H:%M'),
        'logo_path': static('base/img/inemo.png'),
        'proyecto_nombre': nombre_proyecto,
        'fecha_inicio': fecha_inicio_str, # Usamos las cadenas formateadas
        'fecha_fin': fecha_fin_str,       # Usamos las cadenas formateadas
        'proveedores': proveedor_nombres,
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_materiales.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response

# ... (otras vistas si las tienes)

# ====================================================================
# Ejemplos de vistas de detalle o relacionadas que no se piden cambiar
# pero que podrían necesitarse para el funcionamiento completo
# ====================================================================

# Vistas para el autocompletado de materiales (ej. si usas AJAX)
# def get_materiales_ajax(request):
#     query = request.GET.get('q', '')
#     materiales = Material.objects.filter(descripcion__icontains=query).values('id', 'descripcion')[:10]
#     return JsonResponse(list(materiales), safe=False)

# def get_material_detail_ajax(request):
#     material_id = request.GET.get('material_id')
#     try:
#         material = Material.objects.get(pk=material_id)
#         data = {
#             'descripcion': material.descripcion,
#             # Agrega aquí cualquier otro campo que necesites del material
#         }
#         return JsonResponse(data)
#     except Material.DoesNotExist:
#         return JsonResponse({'error': 'Material no encontrado'}, status=404)

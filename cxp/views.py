from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import FormView
from django.views import generic
from django.templatetags.static import static

from django.http import JsonResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import(Proveedor, CompraEnc, CompraDet)
from adm.models import(Proyecto, TipoDocumento, Cuenta)

from inv.models import Material
#from .calculos import calcular_nomina_semanal_todos

from .forms import( ProveedorForm, CompraEncForm )

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
from django.db.models import Sum, Max
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


ffont_path = os.path.join(settings.BASE_DIR, "static/fonts/Arial.ttf")
pdfmetrics.registerFont(TTFont("Arial", font_path))


# Establecer idioma español para los nombres de los meses
locale.setlocale(locale.LC_TIME, "es_ES.utf8")



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
    
    def form_valid(self, form):
        # Calculas el importe antes de guardar
        compra_detalle = form.save(commit=False)
        compra_detalle.importe = compra_detalle.cantidad * compra_detalle.precio_unitario
        compra_detalle.save()
        return super().form_valid(form)
  
  
#@login_required(login_url='/login/')
#@permission_required('cmp.view_comprasb',login_url='bases:sin_privilegios')

def compras(request, compra_id=None):
    template_name = 'cxp/compras.html'
    materialx = Material.objects.filter(estado=True)
    
    # Listas de proveedores, proyectos y tipos de documento
    proveedores = Proveedor.objects.filter(estado=True)
    proyectos = Proyecto.objects.filter(estado=True)
    tipos = TipoDocumento.objects.all()
    form_compras={}

    contexto = {
        'materiales': materialx,
        'proveedores': proveedores,
        'proyectos': proyectos,
        'tipos': tipos,
    }

    if request.method == 'GET':
        form_compras=CompraEncForm
        enc = CompraEnc.objects.filter(pk=compra_id).first()
        
        if enc:
            det = CompraDet.objects.filter(compra=enc)
            #fecha = datetime.date.isoformat(enc.fecha)
            fecha = enc.fecha.isoformat()
            
            
            e = {
                'fecha':fecha,
                'proveedor':enc.proveedor.id,
                'tipo':enc.tipo.id,
                'proyecto':enc.proyecto.id,
                'inventario':enc.inventario,
                'folio_documento':enc.folio_documento,
                'dias_credito':enc.dias_credito,
                'orden_compra':enc.orden_compra,
                'total':enc.total
                
            }
            form_compras=CompraEncForm(e)
        else:
            det=None
        
        contexto={'materiales':materialx,'encabezado':enc,'detalle':det,'form_enc':form_compras}
        
    if request.method=='POST':
            fecha = request.POST.get('fecha')
            proveedor_id = request.POST.get('proveedor')
            proyecto_id = request.POST.get('proyecto')
            tipo_id = request.POST.get('tipo')
            inventario = request.POST.get('inventario')
            folio_documento = request.POST.get('folio_documento')
            dias_credito = request.POST.get('dias_credito')
            orden_compra = request.POST.get('orden_compra')
            total = 0
            
            
            proveedor = Proveedor.objects.get(pk=proveedor_id)
            proyecto = Proyecto.objects.get(pk=proyecto_id)
            tipo = TipoDocumento.objects.get(pk=tipo_id)

                        
            if not compra_id:
                
                enc = CompraEnc(
                    fecha = fecha,
                    proyecto = proyecto,
                    proveedor = proveedor,
                    tipo = tipo,
                    folio_documento = folio_documento,
                    orden_compra = orden_compra,
                    dias_credito = dias_credito,
                    uc=request.user
                )
                if enc:
                    enc.save()
                    compra_id=enc.id
            else:
                enc=CompraEnc.objects.filter(pk=compra_id).first()
                if enc:
                    enc.fecha = fecha
                    enc.proyecto = proyecto
                    enc.proveedor = proveedor
                    enc.folio_documento=folio_documento
                    enc.dias_credito=dias_credito
                    enc.orden_compra=orden_compra
                    enc.um = request.user.id
                    enc.save()
                    
                    material = Material.objects.get(pk=request.POST.get('id_id_producto'))
                    cantidad = request.POST.get('id_cantidad_detalle')
                    precio_unitario = request.POST.get('id_precio_detalle')


                    print(request.POST.get('id_material'))  # Verifica si estás recibiendo el valor esperado
                    print(request.POST.get('id_cantidad_detalle'))  # Verifica si el valor es correcto
                    print(request.POST.get('material.id'))
                    print(request.POST.get('id_id_producto'))

            
            if not compra_id:
                return redirect('cxp:compras_list')
            
            
            material_id = request.POST.get('id_id_producto')
            material = Material.objects.get(pk=material_id)            
            print(material_id+' producto ')
            cantidad = request.POST.get('id_cantidad_detalle')
            precio_unitario=request.POST.get('id_precio_detalle')
            importe=0
        
            det = CompraDet(
                compra = enc,
                material = material,
                cantidad = cantidad,
                precio_unitario = precio_unitario,
                uc = request.user
            )
            if det:
                det.importe = importe
                det.save()
                
                importe = CompraDet.objects.filter(compra=compra_id).aggregate(Sum('importe'))
                enc.total = importe['importe__sum'] if ['importe__sum'] else 0
                enc.save()
                
            return redirect('cxp:compras_edit',compra_id=compra_id)
            
            
            
        
    return render(request, template_name, contexto)



class CompraDetDelete(LoginRequiredMixin, generic.DeleteView):
    model = CompraDet
    template_name = "cxp/compras_det_del.html"
    context_object_name = 'obj'

    def get_success_url(self):
        compra_id = self.kwargs['compra_id']
        
        return reverse_lazy('cxp:compras_edit', kwargs={'compra_id': compra_id})

    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Agregar depuración aquí
        print(f"Producto a eliminar: {self.object.producto.nombre}")

        compra = self.object.compra
        response = super().delete(request, *args, **kwargs)

        # Actualizar el total de la compra
        total = compra.detalle_set.aggregate(total=Sum('importe'))['total'] or 0
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

from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import FormView
from django.views import generic
from django.http import JsonResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import( Cuenta, Proyecto, 
                     ProductoInmobiliario,
                    Venta, Movimiento, Cliente, ReciboPago
                    )

from inv.models import Material
#from .calculos import calcular_nomina_semanal_todos

from .forms import( ValoresConstantesForm, ProductoInmobiliarioForm,
                   VentaForm, MovimientoForm, AsignarClienteForm, ClienteForm)

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
import datetime
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


# Create your views here.


class CrearProductoInmobiliarioView(generic.View):
    template_name = 'ventas/producto_inmobiliario_form.html'

    def get(self, request):
        form = ValoresConstantesForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ValoresConstantesForm(request.POST)
        if form.is_valid():
            precio = form.cleaned_data['precio']
            medidas = form.cleaned_data['medidas']
            proyecto = form.cleaned_data['proyecto']
            cantidad = form.cleaned_data['cantidad']
            

            # Obtener el último número único
            ultimo_numero = ProductoInmobiliario.objects.aggregate(Max('clave'))['clave__max'] or 0

            # Crear los registros
            nuevos_registros = []
            for i in range(1, cantidad + 1):
                nuevos_registros.append(
                    ProductoInmobiliario(
                        clave=ultimo_numero + i,
                        precio=precio,
                        saldo=precio,
                        medidas=medidas,
                        proyecto=proyecto,
                        proceso = 'Disponible',
                        estado=True,
                        fc = now(),
                        tipo = 1,
                        uc = request.user
                    )
                )
            ProductoInmobiliario.objects.bulk_create(nuevos_registros)

            messages.success(request, f'Se han creado {cantidad} registros exitosamente.')
            return redirect('ven:crear_producto_inmobiliario')

        return render(request, self.template_name, {'form': form})
    


# Listar productos inmobiliarios
class ProductoInmobiliarioListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "ventas.view_productoinmobiliario"
    model = ProductoInmobiliario
    template_name = 'ventas/productoinmobiliario_list.html'  # Debes crear este archivo HTML
    context_object_name = 'productos'
    login_url = "bases:login"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('-id')  # Ordena los productos por ID descendente


# Crear un producto inmobiliario
class ProductoInmobiliarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, generic.CreateView):
    permission_required = "ventas.add_productoinmobiliario"
    model = ProductoInmobiliario
    form_class = ProductoInmobiliarioForm
    template_name = 'ventas/productoinmobiliario_form.html'
    success_url = reverse_lazy('ven:productoinmobiliario_list')
    login_url = "bases:login"
    success_message = 'Producto inmobiliario creado satisfactoriamente'

    def form_valid(self, form):
        form.instance.uc = self.request.user  # Asigna el usuario que creó el producto
        return super().form_valid(form)


# Actualizar un producto inmobiliario
class ProductoInmobiliarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, generic.UpdateView):
    permission_required = "ventas.change_productoinmobiliario"
    model = ProductoInmobiliario
    form_class = ProductoInmobiliarioForm
    template_name = 'ventas/productoinmobiliario_edit.html'
    success_url = reverse_lazy('ven:productoinmobiliario_list')
    login_url = "bases:login"
    success_message = 'Producto inmobiliario actualizado satisfactoriamente'

    def form_invalid(self, form):
        print(self.request.POST)
        print(form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        form.instance.clave = self.object.clave  # Restaura el valor del campo
        form.instance.um = self.request.user.id    # Asigna el usuario que modificó
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        print(context['form'].initial)  # Revisa si los valores de clave y saldo están presentes
        return context



# Eliminar un producto inmobiliario
class ProductoInmobiliarioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView):
    permission_required = "ventas.delete_productoinmobiliario"
    model = ProductoInmobiliario
    template_name = 'ventas/productoinmobiliario_del.html'  # Debes crear este archivo HTML
    context_object_name = 'producto'
    success_url = reverse_lazy('ven:productoinmobiliario_list')
    login_url = "bases:login"

class VentaCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, generic.CreateView):
    permission_required = "ventas.add_venta"
    model = Venta
    form_class = VentaForm
    template_name = 'ventas/venta_form.html'
    success_url = reverse_lazy('ventas:venta_list')
    success_message = 'Venta registrada satisfactoriamente'

    def form_valid(self, form):
        form.instance.total = form.instance.producto.precio  # Asignar el total basado en el precio del producto
        return super().form_valid(form)
    
class RegistrarVentaView(generic.CreateView):
    model = Venta
    form_class = VentaForm
    template_name = 'ventas/registrar_venta.html'

    def form_valid(self, form):
        # Calcular el saldo restante
        producto = form.cleaned_data['producto']
        anticipo = form.cleaned_data['anticipo']
        saldo_restante = producto.precio - anticipo
        form.instance.saldo_restante = saldo_restante
        return super().form_valid(form)

    def get_success_url(self):
        return redirect('ven:productoinmobiliario_list')
    


def vender_producto(request, producto_id):
    producto = get_object_or_404(ProductoInmobiliario, id=producto_id)
    
    if producto.proceso != 'Disponible':
        messages.error(request, 'El producto ya ha sido vendido.')
        return redirect('ven:productoinmobiliario_list')

    if request.method == 'POST':
        venta_form = VentaForm(request.POST)
        movimiento_form = MovimientoForm(request.POST)
        
        if venta_form.is_valid() and movimiento_form.is_valid():
            # Asignar cliente al producto
            cliente = venta_form.cleaned_data['cliente']
            producto.proceso = 'Vendido'
            producto.cliente = cliente  # Relación con cliente
            producto.save()

            # Crear movimiento de pago
            movimiento = movimiento_form.save(commit=False)
            movimiento.producto = producto
            movimiento.cliente = cliente
            movimiento.uc_id = request.user.id
            movimiento.save()

            if movimiento.monto > producto.saldo:
                messages.error(request, 'El monto excede el saldo pendiente.')
                return redirect('ven:registrar_pago', producto_id=producto.id)

            producto.saldo -= movimiento.monto  # Restar el monto al saldo actual
            producto.save()


            
            messages.success(request, f'El producto "{producto.clave}" ha sido vendido exitosamente y el movimiento registrado.')
            return redirect('ven:productoinmobiliario_list')
    else:
        venta_form = VentaForm()
        movimiento_form = MovimientoForm()

    return render(request, 'ventas/vender_producto.html', {
        'producto': producto,
        'venta_form': venta_form,
        'movimiento_form': movimiento_form,
    })


def asignar_cliente(request, producto_id):
    # Obtener el producto seleccionado
    producto = get_object_or_404(ProductoInmobiliario, id=producto_id)
    
    if request.method == 'POST':
        # Procesar el formulario enviado
        form = AsignarClienteForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.producto = producto
            movimiento.uc_id=request.user.id
            movimiento.save()
            return redirect(reverse('ven:productoinmobiliario_list'))  # Redirigir después de guardar
    else:
        # Mostrar el formulario vacío
        form = AsignarClienteForm()
    
    return render(request, 'ventas/asignar_cliente.html', {'producto': producto, 'form': form})




def generar_recibo_pdf(movimiento):
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    # Agregar logotipo
    c.drawImage('ruta_a_logotipo.png', 50, 750, width=150, height=50)
    # Información del recibo
    c.drawString(50, 700, f"Recibo para Cliente: {movimiento.cliente.nombre}")
    c.drawString(50, 680, f"Producto: {movimiento.producto.clave}")
    c.drawString(50, 660, f"Monto: ${movimiento.monto}")
    c.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"recibo_{movimiento.id}.pdf")


class ClienteList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "ven.view_cliente"
    model = Cliente
    template_name = 'ventas/cliente_list.html'
    context_object_name = 'clientes'
    login_url = "bases:login"


class ClienteNew(LoginRequiredMixin, generic.CreateView):
    model = Cliente
    fields = ['nombre', 'curp', 'identificacion', 'tipo_identificacion', 'telefono', 'email', 'documento_comprobatorio']
    template_name = 'ventas/cliente_form.html'
    success_url = reverse_lazy('ven:cliente_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class ClienteEdit(LoginRequiredMixin, generic.UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'ventas/cliente_form.html'
    success_url = reverse_lazy('ven:cliente_list')
    login_url = 'bases:login'

       
    def form_valid(self, form):
        form.instance.um = self.request.user.id
        print("Datos del formulario validados:", form.cleaned_data)
        return super().form_valid(form)
    


class ClienteDel(LoginRequiredMixin, generic.DeleteView):
    model = Cliente
    template_name = 'ventas/cliente_del.html'
    success_url = reverse_lazy('ven:cliente_list')
    login_url = 'bases:login'


def registrar_pago(request, producto_id):
    producto = get_object_or_404(ProductoInmobiliario, id=producto_id)

    if producto.proceso != 'Vendido':
        messages.error(request, 'El producto debe estar vendido para registrar pagos.')
        return redirect('ven:productoinmobiliario_list')

    cliente = producto.cliente  # Cliente asignado al producto

    if request.method == 'POST':
        movimiento_form = MovimientoForm(request.POST, request.FILES)  # Incluye archivos
        if movimiento_form.is_valid():
            movimiento = movimiento_form.save(commit=False)
            movimiento.producto = producto
            movimiento.cliente = cliente
            movimiento.uc_id = request.user.id
            movimiento.save()

            # Actualizar saldo del producto
            if movimiento.monto > producto.saldo:
                messages.error(request, 'El monto excede el saldo pendiente.')
                return redirect('ven:registrar_pago', producto_id=producto.id)

            producto.saldo -= movimiento.monto
            producto.save()

            messages.success(
                request,
                f'El pago de {movimiento.monto} ha sido registrado exitosamente para el producto "{producto.clave}".'
            )
            return redirect('ven:productoinmobiliario_list')
    else:
        movimiento_form = MovimientoForm()

    return render(request, 'ventas/registrar_pago.html', {
        'producto': producto,
        'cliente': cliente,
        'movimiento_form': movimiento_form,
    })


def cliente_create_modal(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)  # No guarda aún en la BD
            cliente.uc_id = request.user.id # Asigna el usuario actual
            cliente.save()  # Guarda en la BD
            return redirect('ven:cliente_list')
        else:
            form=ClienteForm()
            return render(request, 'ventas/cliente_form.html', {'form': form})
        
def generar_recibos(venta):
    if venta.tipo_pago == 'Enganche':
        monto_por_cuota = (venta.total * (1 + venta.intereses / 100)) / venta.cuotas
        fecha_actual = venta.fecha_venta
        for numero in range(1, venta.cuotas + 1):
            ReciboPago.objects.create(
                venta=venta,
                numero_pago=numero,
                monto=monto_por_cuota,
                fecha_vencimiento=fecha_actual + timedelta(days=30 * numero)
            )



def buscar_clientes(request):
    q = request.GET.get('q', '')  # Obtén el término de búsqueda
    clientes = Cliente.objects.filter(nombre__icontains=q)[:10]  # Limita los resultados
    results = [{'id': c.id, 'text': c.nombre} for c in clientes]
    return JsonResponse({'results': results})




def generar_recibo_pago(request, recibo_id):
    # Aquí puedes obtener los datos del recibo desde tu base de datos
    recibo = {
        "empresa": "Inmobiliario Morales",
        "logotipo": "static/base/img/inemo.png",  # Ruta al logotipo
        "usuario": request.user.get_full_name(),
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "hora": datetime.now().strftime("%H:%M:%S"),
        "cliente": "Juan Pérez",
        "monto": 1234.56,
        "concepto": "Pago de servicios"
    }

    # Crear el buffer para el PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logotipo
    if recibo["logotipo"]:
        pdf.drawImage(recibo["logotipo"], 30, height - 100, width=100, height=50, preserveAspectRatio=True, mask='auto')

    # Información de la empresa
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(150, height - 50, recibo["empresa"])

    # Título del recibo
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 100, "RECIBO DE PAGO")

    # Detalles del recibo
    pdf.setFont("Helvetica", 10)
    pdf.drawString(30, height - 150, f"Fecha: {recibo['fecha']}")
    pdf.drawString(30, height - 170, f"Hora: {recibo['hora']}")
    pdf.drawString(30, height - 190, f"Usuario: {recibo['usuario']}")
    pdf.drawString(30, height - 210, f"Cliente: {recibo['cliente']}")
    pdf.drawString(30, height - 230, f"Monto: ${recibo['monto']:.2f}")
    pdf.drawString(30, height - 250, f"Concepto: {recibo['concepto']}")

    # Espacios para firmas
    pdf.setFont("Helvetica", 10)
    pdf.drawString(30, height - 300, "______________________________")
    pdf.drawString(30, height - 320, "Firma del Cliente")
    pdf.drawString(300, height - 300, "______________________________")
    pdf.drawString(300, height - 320, "Firma del Usuario")

    # Finalizar el PDF
    pdf.showPage()
    pdf.save()

    # Preparar el archivo para ser descargado
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recibo_{recibo_id}.pdf"'
    return response



def dashboard(request):
    total_clientes = Cliente.objects.count()
    
    # Verifica si esta consulta devuelve objetos
    lotes_venta_qs = ProductoInmobiliario.objects.filter(proceso='Disponible')
    lotes_en_venta = lotes_venta_qs.count()

    lotes_comprados_qs = ProductoInmobiliario.objects.filter(proceso='Vendido')
    lotes_comprados = lotes_comprados_qs.count()

    print("Lotes en venta:", lotes_venta_qs)  # Debug
    print("Lotes comprados:", lotes_comprados_qs)  # Debug

    context = {
        'total_clientes': total_clientes,
        'lotes_en_venta': lotes_en_venta,
        'lotes_comprados': lotes_comprados,
    }
    return render(request, 'ventas/tablero.html', context)
    #return HttpResponse("<h1 style='color: red;'>LLEGASTE AL VIEW</h1>")

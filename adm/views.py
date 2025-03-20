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
from .models import( Banco, Cuenta, Residente, Proyecto, TipoDocumento,
                    Simbologia, Equipo, Bitacora, RegistroCuenta, TipoPago, Pago
                    )

from inv.models import Material
from cxp.models import Proveedor, CompraEnc
#from .calculos import calcular_nomina_semanal_todos

from .forms import( BancoForm, CuentaForm, ResidenteForm, TipoDocumentoForm, ProyectoForm, 
                   SimbologiaForm, PagoForm,
                   ReporteMovimientoForm, EquipoForm, BitacoraForm, TipoPagoForm, RegistroCuentaForm)

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
from django.utils.dateparse import parse_date






pdfmetrics.registerFont(TTFont("Arial", "Arial.ttf"))


# Establecer idioma español para los nombres de los meses
locale.setlocale(locale.LC_TIME, "es_ES.utf8")


class BancoView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_banco"
    model = Banco
    template_name = "adm/banco_list.html"
    context_object_name = "bancos"
    login_url = "bases:login"

class BancoNew(LoginRequiredMixin, generic.CreateView):
    model = Banco
    template_name = "adm/banco_form.html"
    form_class = BancoForm
    success_url = reverse_lazy("adm:banco_list")
    login_url = "bases:login"

    def form_valid(self, form):
        return super().form_valid(form)

class BancoEdit(LoginRequiredMixin, generic.UpdateView):
    model = Banco
    template_name = "adm/banco_form.html"
    form_class = BancoForm
    success_url = reverse_lazy("adm:banco_list")
    login_url = "bases:login"

    def form_valid(self, form):
        return super().form_valid(form)
    
class BancoDel(LoginRequiredMixin, generic.DeleteView):
    model = Banco
    template_name = "adm/banco_del.html"
    context_object_name = "obj"
    login_url = "bases:login"


class CuentaView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_cuenta"
    model = Cuenta
    template_name = "adm/cuenta_list.html"
    context_object_name = "cuentas"
    login_url = "bases:login"
    
t_cuenta = [
    ('General', 'General'),
    ('Proyecto', 'Proyecto')
]

class CuentaNew(LoginRequiredMixin, generic.CreateView):
    model = Cuenta
    template_name = "adm/cuenta_form.html"
    form_class = CuentaForm
    success_url = reverse_lazy("adm:cuenta_list")
    login_url = "bases:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bancos'] = Banco.objects.all()  # Obtiene todos los bancos
        context['t_cuenta'] = t_cuenta
        return context
    
    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class CuentaEdit(LoginRequiredMixin, generic.UpdateView):
    model = Cuenta
    template_name = "adm/cuenta_form.html"
    form_class = CuentaForm
    context_object_name = 'obj'
    success_url = reverse_lazy("adm:cuenta_list")
    login_url = "bases:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bancos'] = Banco.objects.all()  # Obtiene todos los bancos
        context['t_cuenta'] = t_cuenta
        return context
    
    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

        
class ResidenteView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "inv.view_residente"
    model = Residente
    template_name = "adm/residente_list.html"
    context_object_name = "residentes"
    login_url = "bases:login"

class ResidenteNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Residente
    template_name = "adm/residente_form.html"
    form_class = ResidenteForm
    success_url = reverse_lazy("adm:residente_list")
    login_url = "bases:login"
    success_message='Residente registrado satifactoriamente'

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class ResidenteEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Residente
    template_name = "adm/residente_form.html"
    form_class = ResidenteForm
    context_object_name = "obj"    
    success_url = reverse_lazy("adm:residente_list")
    login_url = "bases:login"
    success_message='Residente actualizado satifactoriamente'

class ResidenteDel(SuccessMessageMixin, LoginRequiredMixin, generic.DeleteView):
    model = Residente
    template_name = "adm/residente_list.html"
    context_object_name = "residentes"
    login_url = "bases:login"


class ProyectoView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_proyecto"
    model = Proyecto
    template_name = "adm/proyecto_list.html"
    context_object_name = "proyectos"
    login_url = "bases:login"

class ProyectoNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Proyecto
    template_name = "adm/proyecto_form.html"
    form_class = ProyectoForm
    success_url = reverse_lazy("adm:proyecto_list")
    login_url = "bases:login"
    success_message='Proyecto registrado satifactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['residentes'] = Residente.objects.all()
        context['cuentas'] = Cuenta.objects.all()
        return context
    
    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class ProyectoEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Proyecto
    template_name = "adm/proyecto_form.html"
    form_class = ProyectoForm
    success_url = reverse_lazy("adm:proyecto_list")
    success_message='Proyecto actualizado satisfactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['obj'] = self.object
        context['residentes'] = Residente.objects.all()  # Asegúrate de que esto obtenga todos los residentes
        context['cuentas'] = Cuenta.objects.all()        # Asegúrate de que esto obtenga todas las cuentas
        return context
    
    def form_valid(self, form):
        form.instance.um = self.request.user.id
        estado = self.request.POST.get('estado') == 'on'
        form.instance.estado = estado
        return super().form_valid(form)

    
class ProyectoDel(LoginRequiredMixin, generic.DeleteView):
    model = Proyecto
    template_name = "adm/proyecto_list.html"
    context_object_name = "proyectos"
    login_url = "bases:login"




def proyecto_report(request):
    proyectos = Proyecto.objects.filter(estado=True)  # Filtrar proyectos vigentes
    context = {'proyectos': proyectos}

    # Renderizar la plantilla HTML
    html = render_to_string('adm/proyecto_report.html', context)

    # Crear el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="proyectos_vigentes.pdf"'

    # Convertir HTML a PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error al generar PDF')

    return response


escoge_tipo = [
    ('Padre','Padre'),
    ('Hijo','Hijo')
]
# ListView para listar las simbologías
class SimbologiaView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_simbologia"
    model = Simbologia
    template_name = "adm/simbologia_list.html"  # El template donde mostrarás la lista
    context_object_name = "obj"
    login_url = "bases:login"
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Simbologia.objects.filter(descripcion__icontains=query)
        return Simbologia.objects.all()

# CreateView para crear una nueva simbología
class SimbologiaNew(LoginRequiredMixin, generic.CreateView):
    model = Simbologia
    template_name = "adm/simbologia_form.html"  # El template para el formulario de creación
    context_object_name = "obj"
    form_class = SimbologiaForm  # Asumiendo que tienes un formulario para el modelo Simbologia
    success_url = reverse_lazy("adm:simbologia_list")  # Redirecciona a la lista de simbologías después de crear
    login_url = "bases:login"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escoge_tipo'] = escoge_tipo
        return context

    
# UpdateView para editar una simbología existente
class SimbologiaEdit(LoginRequiredMixin, generic.UpdateView):
    model = Simbologia
    template_name = "adm/simbologia_form.html"  # El mismo template que en la creación, para reutilizar
    context_object_name = "obj"
    form_class = SimbologiaForm
    success_url = reverse_lazy("adm:simbologia_list")  # Redirecciona a la lista de simbologías después de editar
    login_url = "bases:login"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escoge_tipo'] = escoge_tipo
        return context

    
         

class SimbologiaDelete(LoginRequiredMixin, generic.DeleteView):
    model = Simbologia
    template_name = "adm/simbologia_confirm_delete.html"  # El template para confirmar la eliminación
    context_object_name = "obj"
    success_url = reverse_lazy("adm:simbologia_list")  # Redirige a la lista de simbologías después de eliminar
    login_url = "bases:login"



def simbologia_pdf(request):
    # Obtener el listado de simbologías
    simbologias = Simbologia.objects.all()
    
    # Cargar la plantilla HTML
    template_path = 'adm/simbologia_pdf.html'
    context = {'simbologias': simbologias}
    
    # Renderizar la plantilla con los datos
    template = get_template(template_path)
    html = template.render(context)
    
    # Crear una respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="simbologias.pdf"'
    
    # Crear el PDF usando xhtml2pdf
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    # Verificar errores
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF', status=400)
    
    return response




  
  




# views.py

class EquipoListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_equipo"
    model = Equipo
    template_name = 'adm/equipo_list.html'
    context_object_name = 'equipos'

class EquipoCreateView(LoginRequiredMixin, generic.CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'adm/equipo_form.html'
    success_url = '/adm/equipo/'  # Redirigir a la lista después de crear
    
    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)

class EquipoUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'adm/equipo_form.html'
    success_url = '/adm/equipo/'  # Redirigir a la lista después de editar
    
    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

    def get_object(self):
        return get_object_or_404(Equipo, pk=self.kwargs['pk'])

class EquipoDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Equipo
    template_name = 'adm/equipo_confirm_delete.html'
    success_url = '/adm/equipo/'  # Redirigir a la lista después de eliminar

    def get_object(self):
        return get_object_or_404(Equipo, pk=self.kwargs['pk'])
    
    
def obtener_cuenta(cuenta_id):
    try:
        return Cuenta.objects.get(id=cuenta_id)
    except Cuenta.DoesNotExist:
        return None  # O maneja el error de la forma que desees

    


    
class BitacoraListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_bitacora"
    model = Bitacora
    template_name = 'adm/bitacora_list.html'  # Debes crear este archivo HTML
    context_object_name = 'bitacoras'
    login_url = "bases:login"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        print(queryset)  # Verifica qué se está pasando
        return queryset

# Crear una entrada de bitácora
class BitacoraCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, generic.CreateView):
    permission_required = "adm.add_bitacora"
    model = Bitacora
    form_class = BitacoraForm
    template_name = 'adm/bitacora_form.html'
    success_url = reverse_lazy('adm:bitacora_list')
    login_url = "bases:login"
    success_message = 'Bitácora registrada satisfactoriamente'
    
    def form_valid(self, form):
        form.instance.uc = self.request.user  # Asigna al usuario actual
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proyectos'] = Proyecto.objects.all()  # Pasa todos los proyectos
        context['residente'] = Residente.objects.all()  # Pasa todos los responsables
        return context
    
# Actualizar una entrada de bitácora
class BitacoraUpdateView(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    permission_required = "adm.change_bitacora"
    model = Bitacora
    form_class = BitacoraForm
    template_name = 'adm/bitacora_form.html'
    success_url = reverse_lazy('adm:bitacora_list')
    login_url = "bases:login"
    
    def form_valid(self, form):
        form.instance.um = self.request.user.id  # Agrega al usuario que actualiza la bitácora
        return super().form_valid(form)

# Eliminar una entrada de bitácora
class BitacoraDeleteView(LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView):
    permission_required = "adm.delete_bitacora"
    model = Bitacora
    template_name = 'adm/bitacora_del.html'  # Debes crear este archivo HTML
    context_object_name = 'obj'
    success_url = reverse_lazy('adm:bitacora_list')
    login_url = "bases:login"


def registro_cuenta_form(request, id=None):
    obj = None
    if id:
        obj = RegistroCuenta.objects.get(pk=id)

    cuentas = Cuenta.objects.all()
    proveedores = Proveedor.objects.all()

    return render(request, 'tu_template.html', {
        'obj': obj,
        'cuentas': cuentas,
        'proveedores': proveedores
    })

        

def realizar_pago(request, compra_id):
    compra = get_object_or_404(CompraEnc, id=compra_id)
    tipos_pago = TipoPago.objects.all()

    if request.method == "POST":
        tipo_pago_id = request.POST.get("tipo_pago")
        monto = float(request.POST.get("monto"))

        tipo_pago = get_object_or_404(TipoPago, id=tipo_pago_id)
        saldo_pendiente = compra.total - sum(p.monto for p in compra.pagos.all())

        if monto > saldo_pendiente:
            messages.error(request, "El pago excede el saldo pendiente.")
            return redirect('adm:detalle_compra', compra_id=compra.id)

        Pago.objects.create(compra=compra, tipo_pago=tipo_pago, monto=monto)
        messages.success(request, "Pago registrado con éxito.")
        return redirect('adm:detalle_compra', compra_id=compra.id)

    return render(request, "pagos/formulario_pago.html", {"compra": compra, "tipos_pago": tipos_pago})


def registrocuenta_report(request):
    cuenta_id = request.GET.get('cuenta')
    fecha_desde = request.GET.get('fecha_inicio')
    fecha_hasta = request.GET.get('fecha_fin')

    print(f"Cuenta ID: {cuenta_id}, Fecha desde: {fecha_desde}, Fecha hasta: {fecha_hasta}")

    try:
        if fecha_desde and fecha_hasta:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d')
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d')
        else:
            return HttpResponse("Fechas no válidas.")
    except ValueError:
        print("Fechas no válidas.")
        return HttpResponse("Fechas no válidas.")

    # Filtra los registros según los parámetros recibidos
    movimientos = RegistroCuenta.objects.filter(
        cuenta_id=cuenta_id,
        fecha_movimiento__range=[fecha_desde, fecha_hasta]
    )

    cuenta = obtener_cuenta(cuenta_id)

    return render(request, 'adm/registrocuenta_report.html', {
        'form': ReporteMovimientoForm(),
        'cuenta': cuenta,
        'movimientos': movimientos,
        'logo_url': static('adm/logo_empresa.png'),
    })



def generar_pdf(request):
    cuenta_id = request.GET.get('cuenta')
    fecha_desde = request.GET.get('fecha_inicio')
    fecha_hasta = request.GET.get('fecha_fin')

    # Filtrar registros
    registros = RegistroCuenta.objects.filter(
        cuenta_id=cuenta_id,
        fecha_movimiento__range=[fecha_desde, fecha_hasta]
    )

    # Calcular la suma de las cantidades
    total_cantidad = sum(registro.cantidad for registro in registros if registro.cantidad)

    # Crear respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_registrocuenta.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Ruta del logotipo
    #logo_path = os.path.join(os.getcwd(), "static", "base/img", "inemo.png")
    logo_path = "static/base/img/inemo.png"

    # Agregar el logotipo
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 1 * inch, height - 1.8 * inch, width=1.5 * inch, height=1.5 * inch, preserveAspectRatio=True, mask='auto')

    # Encabezado
    p.setFont("Helvetica-Bold", 16)
    p.drawString(3 * inch, height - 0.5 * inch, "Reporte de Registros de Cuenta")
    p.setFont("Helvetica", 12)
    p.drawString(3 * inch, height - 1.2 * inch, f"Cuenta ID: {cuenta_id}")
    p.drawString(3 * inch, height - 1.4 * inch, f"Desde: {fecha_desde} Hasta: {fecha_hasta}")

    # Tabla de datos
    p.setFont("Helvetica-Bold", 9)
    p.drawString(1 * inch, height - 2 * inch, "ID")
    p.drawString(2 * inch, height - 2 * inch, "Fecha")
    p.drawString(3 * inch, height - 2 * inch, "Concepto")
    p.drawString(4 * inch, height - 2 * inch, "Cantidad")
    p.drawString(5 * inch, height - 2 * inch, "Folio Docto")
    

    p.line(1 * inch, height - 2.05 * inch, 7 * inch, height - 2.05 * inch)

    y = height - 2.3 * inch

    # Rellenar la tabla con datos
    p.setFont("Helvetica", 8)
    for registro in registros:
        p.drawString(1 * inch, y, str(registro.id))
        p.drawString(2 * inch, y, registro.fecha_movimiento.strftime('%d-%m-%Y'))
        p.drawString(3 * inch, y, registro.concepto)
        p.drawString(4 * inch, y, f"{registro.cantidad:.2f}")
        p.drawString(5 * inch, y, registro.folio_documento if registro.folio_documento else "N/A")
       
        y -= 0.3 * inch  # Espacio entre filas

    # Mensaje si no hay registros
    if not registros.exists():
        p.drawString(1 * inch, y, "No se encontraron registros para este rango.")
    else:
        y -= 0.25 * inch  # Espacio antes de la suma
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1 * inch, y, f"Suma Total de Cantidad: {total_cantidad:.2f}")

    p.showPage()
    p.save()
    return response


class ReporteMovimientoView(LoginRequiredMixin, generic.View):
    template_name = 'adm/reporte_movimiento.html'

    def get(self, request, cuenta_id):
        cuenta = get_object_or_404(Cuenta, id=cuenta_id)
        form = ReporteMovimientoForm()
        return render(request, self.template_name, {'form': form, 'movimientos': None, 'cuenta': cuenta})

    def post(self, request, cuenta_id):
        cuenta = get_object_or_404(Cuenta, id=cuenta_id)
        form = ReporteMovimientoForm(request.POST)
        if form.is_valid():
            fecha_inicio = form.cleaned_data['fecha_inicio']
            fecha_fin = form.cleaned_data['fecha_fin']
            movimientos = RegistroCuenta.objects.filter(
                fecha_movimiento__range=(fecha_inicio, fecha_fin),
                cuenta=cuenta
            )
        return render(request, self.template_name, {'form': form, 'movimientos': movimientos, 'cuenta': cuenta})



# Lista de tipos de pago
class TipoPagoListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_tipopago"
    model = TipoPago
    template_name = 'adm/tipopago_list.html'  # Archivo HTML para la lista
    context_object_name = 'tipos_pago'
    login_url = "bases:login"

    def get_queryset(self):
        queryset = super().get_queryset()
        print(queryset)  # Verifica qué se está pasando
        return queryset

# Crear tipo de pago
class TipoPagoCreateView(LoginRequiredMixin, generic.CreateView):
    model = TipoPago
    form_class = TipoPagoForm
    template_name = 'adm/tipopago_form.html'  # Archivo HTML para el formulario
    success_url = reverse_lazy('adm:tipopago_list')
    login_url = "bases:login"

    def form_valid(self, form):
        return super().form_valid(form)

# Actualizar tipo de pago
class TipoPagoUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = TipoPago
    form_class = TipoPagoForm
    template_name = 'adm/tipopago_form.html'
    success_url = reverse_lazy('adm:tipopago_list')
    login_url = "bases:login"

    def form_valid(self, form):
        return super().form_valid(form)

# Eliminar tipo de pago
class TipoPagoDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = TipoPago
    template_name = 'adm/tipopago_del.html'  # Archivo HTML para confirmación
    context_object_name = 'obj'
    success_url = reverse_lazy('adm:tipopago_list')
    login_url = "bases:login"


class RegistroCuentaListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "adm.view_registrocuenta"
    model = RegistroCuenta
    template_name = "adm/registroCuenta_list.html"
    context_object_name = "registros"
    login_url = "bases:login"

class RegistroCuentaCreateNew(LoginRequiredMixin, generic.CreateView):
    model = RegistroCuenta
    template_name = "adm/registroCuenta_form.html"
    form_class = RegistroCuentaForm
    success_url = reverse_lazy("adm:registrocuenta_list")
    login_url = "bases:login"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cuentas'] = Cuenta.objects.all()  # Obtener cuentas
        context['proveedores'] = Proveedor.objects.all()  # Obtener proveedores
        return context

    def form_valid(self, form):
        form.instance.uc = self.request.user
        cuenta = form.instance.cuenta
        
        # Ajusta el saldo según el tipo de movimiento
        if form.instance.reposicion_flujo:
            form.instance.folio_documento = None
            cuenta.saldo_actual += form.instance.cantidad
        else:
            cuenta.saldo_actual -= form.instance.cantidad

        response = super().form_valid(form)
        cuenta.save()  # Guardar los cambios en el saldo
        return response

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)  # Deja que el método save del modelo maneje el saldo



class RegistroCuentaEdit(LoginRequiredMixin, generic.UpdateView):
    model = RegistroCuenta
    template_name = "adm/registroCuenta_form.html"
    form_class = RegistroCuentaForm
    success_url = reverse_lazy("adm:registroCuenta_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cuentas'] = Cuenta.objects.all()  # Obtener cuentas
        context['proveedores'] = Proveedor.objects.all()  # Obtener proveedores
        return context
    
class RegistroCuentaDel(LoginRequiredMixin, generic.DeleteView):
    model = RegistroCuenta
    template_name = "adm/registroCuenta_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("adm:registroCuenta_list")
    login_url = "bases:login"
    


def generar_reporte_RegistroCuentas(request):
    # Obtener los datos de los RegistroCuentas
    RegistroCuentas = RegistroCuenta.objects.all().values('fecha_RegistroCuenta', 'concepto', 'cantidad', 'folio_documento')

    # Crear un PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_RegistroCuentas.pdf"'
    
    pdf = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Crear tabla de datos
    data = [['Fecha', 'Concepto', 'Cantidad', 'Folio Documento', 'Proveedor']]
    for RegistroCuenta in RegistroCuentas:
        data.append([RegistroCuenta['fecha_RegistroCuenta'], RegistroCuenta['concepto'], RegistroCuenta['cantidad'], RegistroCuenta['folio_documento']])
    
    table = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(style)

    elements.append(table)
    pdf.build(elements)
    
    return response


    


class RegistroCuentaReportView(generic.View):
    def get(self, request, start_date, end_date):
        # Filtrar los RegistroCuentas
        RegistroCuentas = RegistroCuenta.objects.filter(fecha_RegistroCuenta__range=[start_date, end_date])
        
        # Si necesitas una cuenta específica, debes obtenerla
        # Suponiendo que la cuenta se relaciona con el primer RegistroCuenta (puedes ajustar esto según tu lógica)
        if RegistroCuentas.exists():
            cuenta = RegistroCuentas.first().cuenta
        else:
            cuenta = None

        # Calcular el total de RegistroCuentas
        total_RegistroCuentas = sum(RegistroCuenta.cantidad for RegistroCuenta in RegistroCuentas)

        # Calcular el saldo final
        if cuenta:
            saldo_final = cuenta.saldo_actual
        else:
            saldo_final = 0  # O maneja según tu lógica

        # Preparar el contexto para la plantilla
        context = {
            'RegistroCuentas': RegistroCuentas,
            'total_RegistroCuentas': total_RegistroCuentas,
            'saldo_final': saldo_final,
            'start_date': start_date,
            'end_date': end_date,
        }

        # Generar el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="RegistroCuentas_report.pdf"'

        template_path = 'adm/RegistroCuenta_pdf_template.html'
        html = render_to_string(template_path, context)

        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return HttpResponse('Error al generar el PDF')

        return response



def registrar_pago(request, compra_id):
    compra = get_object_or_404(CompraEnc, id=compra_id)
    
    if request.method == 'POST':
        form = PagoForm(request.POST, compra=compra)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.compra = compra  # ✅ Asegura que la compra se asigna antes de guardar
            
            # Depuración
            print(f"Compra asignada: {pago.compra}")
            print(f"Tipo de pago: {pago.tipo_pago}")
            print(f"Monto: {pago.monto}")

            try:
                pago.save()
                messages.success(request, "Pago registrado correctamente.")
                return redirect('cxp:compras_list')  # ✅ Redirección segura
            except Exception as e:
                messages.error(request, f"Error al registrar el pago: {e}")
    
    else:
        form = PagoForm(initial={'compra': compra})  # ✅ Cargar compra en el formulario

    return render(request, 'adm/registrar_pago.html', {'form': form, 'compra': compra})



def listado_pagos(request):
    pagos = Pago.objects.select_related('compra__proveedor')

    # Capturar filtros de fecha y proveedor
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    proveedor_id = request.GET.get('proveedor')

    if fecha_inicio:
        fecha_inicio = parse_date(fecha_inicio)
        pagos = pagos.filter(fecha__date__gte=fecha_inicio)

    if fecha_fin:
        fecha_fin = parse_date(fecha_fin)
        pagos = pagos.filter(fecha__date__lte=fecha_fin)

    if proveedor_id:
        pagos = pagos.filter(compra__proveedor_id=proveedor_id)

    # Obtener lista de proveedores
    from cxp.models import Proveedor  # Ajusta según tu estructura
    proveedores = Proveedor.objects.all()

    return render(request, 'adm/listado_pagos.html', {'pagos': pagos, 'proveedores': proveedores})


def dashboard(request):
    #total_ventas = Venta.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    #total_nomina = Nomina.objects.aggregate(Sum('monto'))['monto__sum'] or 0
    total_compras = CompraEnc.objects.aggregate(Sum('total'))['total__sum'] or 0

    context = {
    #    'total_ventas': total_ventas,
    #    'total_nomina': total_nomina,
        'total_compras': total_compras,
    }
    return render(request, 'adm/dashboard.html', context)

from django.db.models import Sum, F, Case, When, Value, CharField

def compras_pagadas(request):
    compras = CompraEnc.objects.annotate(
        total_pagado=Sum('pagos__monto', default=0),  # Suma de pagos relacionados
        saldo=F('total') - Sum('pagos__monto', default=0),  # Calcular saldo
        proveedor_nombre=F('proveedor__razon_social'),  # Nombre del proveedor
        estado_calculado=Case(
            When(total_pagado__gte=F('total'), then=Value('pagado')),
            default=Value('pendiente'),
            output_field=CharField()
        )
    ).filter(total_pagado__gt=0)  # Solo compras con pagos

    return render(request, 'adm/listado_saldo_compras.html', {'compras': compras})

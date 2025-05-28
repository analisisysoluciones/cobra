from django.shortcuts import render
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.edit import FormView
from django.views import generic
from django.http import JsonResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import(Cuenta, Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle, 
                    PeriodosNomina, EmpleadoArchivo
                    )

from inv.models import Material
from adm.models import MovimientoCuenta
#from .calculos import calcular_nomina_semanal_todos

from .forms import(EmpleadoForm, FaltaForm, FechaForm, PeriodosNominaForm, EmpleadoArchivoForm)

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
from reportlab.platypus import Paragraph


# Create your views here.

font_path = os.path.join(settings.BASE_DIR, "static/fonts/Arial.ttf")
pdfmetrics.registerFont(TTFont("Arial", font_path))


# Establecer idioma español para los nombres de los meses
#locale.setlocale(locale.LC_TIME, "es_ES.utf8")


def validar_curp(request):
    curp = request.GET.get('curp', '').upper()  # Convertir a mayúsculas
    existe = Empleado.objects.filter(curp=curp).exists()
    return JsonResponse({'existe': existe})


class EmpleadoList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "nomina.view_empleados"
    model = Empleado
    template_name = 'nomina/empleado_list.html'
    context_object_name = 'empleados'
    login_url = "bases:login"
    ordering = ['codigo']


class EmpleadoNew(LoginRequiredMixin, generic.CreateView):
    model = Empleado
    fields =['codigo','rfc','curp','nombre','ingreso','sueldo_diario','compensacion','puesto']
    template_name = 'nomina/empleado_form.html'
    success_url = reverse_lazy('nom:empleado_list')
    login_url = 'bases:login'

       
    def form_valid(self, form):
            form.cleaned_data
            form.instance.uc = self.request.user  # Asigna el usuario creador
            self.object = form.save()  # Guarda el empleado y lo asigna a self.object
            
            # Guardar archivos relacionados con el empleado
            archivos = self.request.FILES.getlist('archivo')  
            nombres = self.request.POST.getlist('nombre')  # Captura los nombres

            for archivo, nombre in zip(archivos,nombres):
                EmpleadoArchivo.objects.create(empleado=self.object, archivo=archivo, nombre = nombres)

            return super().form_valid(form)

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['empleado'] = self.object if self.object else None  # Evitar error en el template
            return context
    

class EmpleadoEdit(LoginRequiredMixin, generic.UpdateView):
    model = Empleado
    form_class = EmpleadoForm
    context_object_name = 'obj'
    template_name = 'nomina/empleado_form.html'
    success_url = reverse_lazy('nom:empleado_list')
    login_url = 'bases:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['archivos'] = EmpleadoArchivo.objects.filter(empleado=self.object)
        return context

def form_valid(self, form):
    try:
        # Guardar el formulario del empleado
        empleado = form.save(commit=False)
        empleado.um = self.request.user.id
        empleado.save()

        # 🔥 DEBUG: Imprimir lo que se está guardando
        print(f"Empleado actualizado: {empleado}")

        # Procesar archivo si se sube uno
        if 'archivo' in self.request.FILES:
            archivo_form = EmpleadoArchivoForm(self.request.POST, self.request.FILES)

            if archivo_form.is_valid():
                archivo = archivo_form.save(commit=False)
                archivo.nombre = self.request.POST.get("nombre_archivo", "").strip()
                archivo.empleado = empleado  # Relacionar con el empleado
                archivo.save()
            else:
                print(f"Errores en archivo: {archivo_form.errors}")  # 🔥 Debug
                return self.form_invalid(form)  # <-- IMPORTANTE: Manejar errores correctamente

        return super().form_valid(form)  # 🔥 Esto debería hacer la redirección
    except Exception as e:
        print(f"❌ Error en form_valid: {e}")
        return self.form_invalid(form)

class EmpleadoDel(LoginRequiredMixin, generic.DeleteView):
    model = Empleado
    template_name = 'nomina/empleado_del.html'
    success_url = reverse_lazy('nom:empleado_list')
    login_url = 'bases:login'

 
    
    


class DocumentoEmpleadoDelete(LoginRequiredMixin, generic.DeleteView):
    model = EmpleadoArchivo
    template_name = "nomina/documento_confirm_delete.html"
    login_url = 'bases:login'

    def get_success_url(self):
        empleado = self.object.empleado
        return reverse_lazy('nom:empleado_edit', kwargs={'pk': empleado.pk})



def vacaciones_empleado(request, empleado_id):
    empleado = Empleado.objects.get(pk=empleado_id)
    return JsonResponse({
        "nombre": empleado.nombre,
        "años_servicio": empleado.años_servicio(),
        "días_vacaciones": empleado.dias_vacaciones(),
    })


# def calcular_nomina_semanal_todos(fecha_inicio_semana):
#     fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    
#     empleados = Empleado.objects.all()
#     nomina_lista = []

#     for empleado in empleados:
#         # Contamos la cantidad de días no trabajados (faltas)
#         faltas = Asistencia.objects.filter(
#             empleado=empleado,
#             fecha__range=[fecha_inicio_semana, fecha_fin_semana],            
#         ).count()

#         sueldo_diario = Decimal(empleado.sueldo_diario)
#         dias_trabajados = Decimal(6)  # Se asume que siempre trabajó 6 días
#         sueldo_semanal = dias_trabajados * sueldo_diario

#         # Calcular séptimo día completo
#         septimo_dia = sueldo_diario

#         # Calcular el importe total por faltas
#         importe_faltas = faltas * sueldo_diario
#         descuento_septimo_dia = (faltas / Decimal(6)) * sueldo_diario


#         # Parte proporcional del séptimo día según asistencias
#         if faltas > 0:
#             proporcion_septimo = (dias_trabajados - faltas) / Decimal(6) * sueldo_diario
#         else:
#             proporcion_septimo = Decimal(0)

#         compensacion = Decimal(empleado.compensacion or 0)

#         # Total a pagar después de descuentos
#         total_pago = sueldo_semanal + septimo_dia + compensacion - importe_faltas - descuento_septimo_dia


#         # Calcular el descuento proporcional del séptimo día según faltas
#         descuento_septimo_dia = (faltas / Decimal(6)) * sueldo_diario

#         # Si el usuario espera ver 85.71, entonces esta es la variable correcta
#         diferencia_septimo_dia = descuento_septimo_dia

#         # Percepciones y deducciones desglosadas
#         percepciones = sueldo_semanal + septimo_dia + compensacion
#         deducciones = importe_faltas + descuento_septimo_dia

#         # Total neto
#         total_pago = percepciones - deducciones
#         if total_pago is None:
#             total_pago = Decimal(0)


            

#         # Añadir los datos a la lista de nómina
#         nomina_lista.append({
#             'empleado': empleado,
#             'sueldo_diario': float(sueldo_diario),
#             'dias_trabajados': int(dias_trabajados),
#             'faltas': faltas,  # Número de días de falta
#             'importe_faltas': float(importe_faltas),  # Importe de las faltas
#             'sueldo_semanal': float(sueldo_semanal - importe_faltas),
#             'septimo_dia': float(septimo_dia),
#             'proporcion_septimo': float(proporcion_septimo),  # Parte proporcional del séptimo día
#             'compensacion': float(compensacion),
#             'total_pago': float(total_pago),
#             'diferencia_septimo_dia': float(diferencia_septimo_dia),  # Ahora mostrará 85.71 si falta 1 día
#             'descuento_septimo_dia': float(descuento_septimo_dia),
#             'percepciones': float(percepciones),
#             'deducciones': float(deducciones),
#             'total_pago': float(total_pago), 
#         })

#     return nomina_lista

def calcular_nomina_semanal_todos(fecha_inicio_semana):
    
    if isinstance(fecha_inicio_semana, str):
        try:
            fecha_inicio_semana = datetime.strptime(fecha_inicio_semana, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Formato de fecha incorrecto. Debe ser 'YYYY-MM-DD'.")
            return []

    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    empleados = Empleado.objects.filter(estado=True)
    
    nomina_lista = []

    for empleado in empleados:
        print(f"Procesando empleado: {empleado.nombre}")
        # Contamos los días que aparecen en Asistencia (son faltas)
        dias_faltados = Asistencia.objects.filter(
            empleado=empleado,
            fecha__range=[fecha_inicio_semana, fecha_fin_semana]            
        ).count()

        

        # Si no hay faltas registradas, significa que trabajó todos los días
        if dias_faltados == 0:
            faltas = 0
        else:
            faltas = dias_faltados  # Ya que asistencia guarda faltas, no asistencias.

        sueldo_diario = Decimal(empleado.sueldo_diario)
        dias_trabajados = Decimal(6) # Decimal(6 - faltas)
        sueldo_semanal = dias_trabajados * sueldo_diario

        # Se paga el séptimo día solo si no hubo faltas
        septimo_dia = sueldo_diario if faltas == 0 else Decimal(0)
        importe_faltas = faltas * sueldo_diario

        # Descuento proporcional del séptimo día si hubo faltas
        descuento_septimo_dia = (faltas / Decimal(6)) * sueldo_diario if faltas > 0 else Decimal(0)
        print(descuento_septimo_dia)

        compensacion = Decimal(empleado.compensacion or 0)
        percepciones = sueldo_semanal + septimo_dia + compensacion
        deducciones = importe_faltas + descuento_septimo_dia
        total_pago = percepciones - deducciones

        nomina_lista.append({
            'empleado': empleado.nombre,
            'ingreso': empleado.ingreso,
            'sueldo_diario': float(sueldo_diario),
            'dias_trabajados': int(dias_trabajados),
            'faltas': faltas,
            'importe_faltas': float(importe_faltas),
            'sueldo_semanal': float(sueldo_semanal),
            'septimo_dia': float(septimo_dia),
            'compensacion': float(compensacion),
            'total_pago': float(total_pago),
            'descuento_septimo_dia': float(descuento_septimo_dia),
            'percepciones': float(percepciones),
            'deducciones': float(deducciones),
        })
    

    return nomina_lista

def calcular_nomina_view(request):
    form = FechaForm()
    nomina = []
    fecha_seleccionada = None
    


    if request.method == "POST":
        form = FechaForm(request.POST)
        if form.is_valid():
            
            fecha_seleccionada = form.cleaned_data['fecha']
            nomina = calcular_nomina_semanal_todos(str(fecha_seleccionada))
            
    return render(request, "nomina/nomina_semanal.html", {
        "form": form,
        "nomina": nomina,
        "fecha": fecha_seleccionada
    })


def capturar_falta(request):
    if request.method == 'POST':
        form = FaltaForm(request.POST)
        if form.is_valid():
            falta = form.save()
            messages.success(request, 'Falta registrada correctamente.')
            return redirect('nom:capturar_falta')  # Redirige a la misma página para capturar más faltas
        else:
            messages.error(request, 'Error al registrar la falta. Verifica los campos.')
    else:
        form = FaltaForm()
    return render(request, 'nomina/capturar_falta.html', {'form': form})


def seleccionar_fecha(request):
    fecha_seleccionada = None  # Variable para almacenar la fecha
    
    if request.method == "POST":
        form = FechaForm(request.POST)
        if form.is_valid():
            fecha_seleccionada = form.cleaned_data['fecha']
            print(f"Fecha seleccionada: {fecha_seleccionada}")  # Ver en consola

    else:
        form = FechaForm()
    
    return render(request, 'nomina/seleccionar_fecha.html', {'form': form, 'fecha': fecha_seleccionada})



def formato_fecha(fecha):
    return fecha.strftime("%d-%B-%Y").capitalize()

def generar_nomina_pdf(request):
    fecha_inicio_semana = datetime.strptime(request.GET.get("fecha", datetime.today().strftime("%Y-%m-%d")), "%Y-%m-%d")
    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)

    nomina = calcular_nomina_semanal_todos(fecha_inicio_semana.strftime("%Y-%m-%d"))

    if not nomina:
        return HttpResponse("No hay datos de nómina", content_type="text/plain")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="nomina.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(legal))

    margen_izquierdo = 25
    margen_superior = 520

    # Insertar logo
    logo_path = "static/base/img/inemo.png"
    try:
        logo = ImageReader(logo_path)
        p.drawImage(logo, margen_izquierdo, margen_superior, width=120, height=60, mask="auto")
    except Exception as e:
        print(f"⚠ No se pudo cargar el logo: {e}")

    # Título
    margen_superior = 570
    titulo = f"Reporte de Nómina del {formato_fecha(fecha_inicio_semana)} al {formato_fecha(fecha_fin_semana)}"
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margen_izquierdo + 150, margen_superior - 15, titulo)

    p.setFont("Helvetica", 8)
    p.drawString(margen_izquierdo + 150, margen_superior - 25, "Domicilio: Puerto Altata 590")
    p.drawString(margen_izquierdo + 150, margen_superior - 40, "RFC: IEM060621IE3")

    # Encabezados y subtítulos
    encabezados = ["Nombre del Empleado", "Percepciones", "", "", "", "", "", "Deducciones", "", "", "", "Total", "Firma"]
    subtitulos = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", ""]

    datos = [encabezados, subtitulos]

    # Inicializar los totales
    totales = {
        "03": 0, "04": 0, "06": 0, "08": 0, "09": 0, "10": 0, "11": 0
    }

    # Agregar filas de datos y calcular totales
    for item in nomina:
        fila = [
            item["empleado"],
            f"${item['sueldo_diario']:.2f}", item["dias_trabajados"], f"${item['sueldo_semanal']:.2f}",
            f"${item['septimo_dia']:.2f}", f"${item['compensacion']:.2f}", f"${item['percepciones']:.2f}",
            item["faltas"], f"${item['importe_faltas']:.2f}", f"${item['descuento_septimo_dia']:.2f}",
            f"${item['deducciones']:.2f}", f"${item['total_pago']:.2f}", ""
        ]

        # Acumular totales en las columnas específicas
        totales["03"] += item['sueldo_semanal']
        totales["04"] += item['septimo_dia']
        totales["06"] += item['percepciones']
        totales["08"] += item['importe_faltas']
        totales["09"] += item['descuento_septimo_dia']
        totales["10"] += item['deducciones']
        totales["11"] += item['total_pago']

        datos.append(fila)

    # Agregar fila de totales
    fila_totales = [
        "TOTAL",
        "", "", f"${totales['03']:.2f}", f"${totales['04']:.2f}", "", f"${totales['06']:.2f}", "",
        f"${totales['08']:.2f}", f"${totales['09']:.2f}", f"${totales['10']:.2f}", f"${totales['11']:.2f}", ""
    ]
    datos.append(fila_totales)

    # Ajustar anchos de columna
    col_widths = [190, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 150]
    row_heights = [20] * len(datos)

    tabla = Table(datos, colWidths=col_widths, rowHeights=row_heights)

    estilos = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),

    # Alineación de encabezados
    ("ALIGN", (1, 0), (6, 0), "CENTER"),
    ("ALIGN", (7, 0), (10, 0), "CENTER"),
    ("ALIGN", (11, 0), (11, 0), "CENTER"),
    ("ALIGN", (12, 0), (12, 0), "CENTER"),

    # Fusionar celdas en los títulos principales
    ("SPAN", (1, 0), (6, 0)),  
    ("SPAN", (7, 0), (10, 0)),  
    ("SPAN", (11, 0), (11, 0)),  
    ("SPAN", (12, 0), (12, 0)),  

    # Alinear subtítulos al centro
    ("ALIGN", (1, 1), (10, 1), "CENTER"),
    ("ALIGN", (12, 1), (12, 1), "CENTER"),

    # Alinear los números a la derecha
    ("ALIGN", (1, 2), (-2, -1), "RIGHT"),  

    # Resaltar la fila de totales
    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("ALIGN", (0, -1), (-1, -1), "LEFT"),  

    # Asegurar que todo el contenido esté centrado y con líneas
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 1, colors.black),

    # Colores de fondo en los encabezados agrupados
    ("BACKGROUND", (1, 0), (6, 0), colors.lightgrey),
    ("BACKGROUND", (7, 0), (10, 0), colors.lightgrey),
    ("BACKGROUND", (11, 0), (11, 0), colors.lightgrey),
    ("BACKGROUND", (12, 0), (12, 0), colors.lightgrey),
])
    

    # Alternar colores en filas de datos
    for i in range(2, len(datos) - 1):
        if i % 2 == 0:
            estilos.add("BACKGROUND", (0, i), (-1, i), colors.whitesmoke)

    tabla.setStyle(estilos)

    tabla.wrapOn(p, 900, 600)
    tabla.drawOn(p, margen_izquierdo, 200)

    # Pie de página
    pie_pagina = (
        "01.- Sueldo diario, 02.- Días trabajados, 03.- Importe días trabajados, "
        "04.- Pago 7mo día, 05.- Compensación, 06.- Total percepciones, "
        "07.- Faltas, 08.- Descuento por falta, 09.- Proporcional 7mo día, "
        "10.- Total deducciones, 11.- Pago neto."
    )

    def agregar_pie_pagina(canvas, doc):
        canvas.setFont("Helvetica", 7)
        canvas.drawString(margen_izquierdo, 30, pie_pagina)

    agregar_pie_pagina(p, None)

    p.save()
    buffer.seek(0)
    response.write(buffer.read())
    return response


def procesar_nomina(request):
    if request.method == "POST":
        fecha_str = request.POST.get("fecha")  
        cuenta_id = request.POST.get("cuenta")  

        if not fecha_str or not cuenta_id:
            return HttpResponse("Faltan datos: fecha o cuenta", content_type="text/plain")
        
        try:
            fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponse("Formato de fecha incorrecto", content_type="text/plain")
        
        periodo_fin = fecha_inicio + timedelta(days=6)
        nomina_data = calcular_nomina_semanal_todos(fecha_str)

        if not nomina_data:
            return HttpResponse("No hay datos de nómina para procesar", content_type="text/plain")
        
        total_nomina = sum(Decimal(item['total_pago']) for item in nomina_data)
        
        try:
            cuenta = Cuenta.objects.get(id=cuenta_id)
        except Cuenta.DoesNotExist:
            return HttpResponse("Cuenta no encontrada", content_type="text/plain")

        # 🔴 Verificar si la cuenta tiene saldo suficiente
        if cuenta.saldo_actual < total_nomina:
            return HttpResponse("Saldo insuficiente en la cuenta", content_type="text/plain")
        
        # 🔹 Descontar la nómina de la cuenta
        cuenta.saldo_actual -= total_nomina
        cuenta.save()
        
        # 🔹 Registrar el retiro en MovimientoCuenta
        MovimientoCuenta.objects.create(
            cuenta=cuenta,
            fecha=fecha_inicio,
            descripcion="Pago de nómina",
            cargo=total_nomina,  # Porque es un retiro
            abono=0,
            saldo=cuenta.saldo_actual
        )
        
        # 🔹 Guardar la cabecera de la nómina
        nomina_hist = NominaHistorial.objects.create(
            periodo_inicio=fecha_inicio,
            periodo_fin=periodo_fin,
            total_pago=total_nomina,
            cuenta=cuenta,
            estatus='Pendiente'
        )
        
        # 🔹 Guardar cada detalle de la nómina
        for item in nomina_data:
            try:
                empleado = Empleado.objects.get(nombre=item["empleado"])
            except Empleado.DoesNotExist:
                continue
            NominaDetalle.objects.create(
                nomina_historica=nomina_hist,
                empleado=empleado,
                sueldo_diario=item["sueldo_diario"],
                dias_trabajados=item["dias_trabajados"],
                total_pago=item["total_pago"]
            )
        
        messages.success(request, "🎉 ¡Éxito! La nómina ha sido procesada y registrada correctamente.")

    cuentas = Cuenta.objects.all()
    return render(request, "nomina/procesar_nomina.html", {"cuentas": cuentas})

LOGO_PATH = "static/base/img/inemo.png"

def generar_nomina_individual_pdf(request):
    fecha_inicio_str = request.GET.get('fecha_inicio', None)

    if not fecha_inicio_str:
        return HttpResponse("Error: Falta el parámetro 'fecha_inicio'", status=400)

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        fecha_fin = fecha_inicio + timedelta(days=6)
    except ValueError:
        return HttpResponse("Error: Formato de fecha inválido, debe ser YYYY-MM-DD", status=400)

    nomina_lista = calcular_nomina_semanal_todos(fecha_inicio)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="nomina_{fecha_inicio}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    for empleado in nomina_lista:
        try:
            p.drawImage(LOGO_PATH, 40, height - 80, width=100, height=50)
        except:
            p.setFillColor(colors.red)
            p.drawString(40, height - 60, "LOGO NO ENCONTRADO")

        p.setFont("Helvetica-Bold", 14)
        p.drawString(200, height - 50, "Recibo de Nómina")

        p.setFont("Helvetica-Bold", 10)
        p.drawString(200, height - 70, f"Periodo: {fecha_inicio} - {fecha_fin}")

        # Agregar domicilio y RFC
        p.setFont("Helvetica", 8)
        p.drawString(200, height - 85, "Domicilio: Puerto Altata 590")
        p.drawString(200, height - 100, "RFC: IEM060621IE3")

        y_position = height - 120  

        p.setFont("Helvetica-Bold", 12)
        p.drawString(40, y_position, f"Empleado: {empleado['empleado']}")
        y_position -= 20  

        # Agregar la fecha de ingreso
        p.setFont("Helvetica", 12)
        p.drawString(40, y_position, f"Fecha de Ingreso: {empleado['ingreso'].strftime('%d/%m/%Y')}")
        y_position -= 30  # Ajusta la posición vertical para los siguientes textos

        

        cuadro_x = 40
        cuadro_y = y_position - 180
        cuadro_ancho = 500
        cuadro_alto = 180
        p.rect(cuadro_x, cuadro_y, cuadro_ancho, cuadro_alto)

        p.line(cuadro_x + (cuadro_ancho / 2), cuadro_y, cuadro_x + (cuadro_ancho / 2), cuadro_y + cuadro_alto)

        p.setFont("Helvetica-Bold", 10)
        p.drawString(cuadro_x + 10, cuadro_y + cuadro_alto - 20, "Percepciones")

        compensacion = empleado.get('compensacion', 0)
        importe_dias_trabajados = empleado['dias_trabajados'] * empleado['sueldo_diario']

        percepciones = [
            ("Sueldo Diario:", empleado['sueldo_diario']),
            ("Días Trabajados:", empleado['dias_trabajados']),
            ("Importe Días Trabajados:", importe_dias_trabajados),
            ("Séptimo Día:", empleado['septimo_dia']),
            ("Compensación:", compensacion),
        ]

        total_percepciones = sum([
            importe_dias_trabajados,
            empleado['septimo_dia'],
            compensacion
        ])  

        y_conceptos = cuadro_y + cuadro_alto - 40
        p.setFont("Helvetica", 10)
        color_actual = colors.whitesmoke  

        for label, valor in percepciones:
            p.setFillColor(color_actual)
            p.rect(cuadro_x + 5, y_conceptos - 5, cuadro_ancho / 2 - 10, 15, fill=1, stroke=0)
            p.setFillColor(colors.black)

            if label == "Días Trabajados:":
                p.drawString(cuadro_x + 10, y_conceptos, f"{label} {valor}")  
            else:
                p.drawString(cuadro_x + 10, y_conceptos, f"{label} ${valor:,.2f}")  

            y_conceptos -= 15
            color_actual = colors.white if color_actual == colors.whitesmoke else colors.whitesmoke

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(cuadro_x + 10, y_conceptos - 10, f"Total Percepciones: ${total_percepciones:,.2f}")

        p.setFont("Helvetica-Bold", 10)
        p.drawString(cuadro_x + 260, cuadro_y + cuadro_alto - 20, "Deducciones")

        deducciones = [
            ("Faltas:", empleado['faltas']),
            ("Descuento por falta:", empleado['importe_faltas']),
            ("Descuento 7mo día:", empleado['descuento_septimo_dia']),
            ("Total Deducciones:", empleado['deducciones']),
        ]

        y_conceptos = cuadro_y + cuadro_alto - 40
        p.setFont("Helvetica", 10)
        color_actual = colors.whitesmoke  

        for label, valor in deducciones:
            p.setFillColor(color_actual)
            p.rect(cuadro_x + 255, y_conceptos - 5, cuadro_ancho / 2 - 10, 15, fill=1, stroke=0)
            p.setFillColor(colors.black)

            if label == "Faltas:":
                p.drawString(cuadro_x + 260, y_conceptos, f"{label} {valor}")  
            else:
                p.drawString(cuadro_x + 260, y_conceptos, f"{label} ${valor:,.2f}")  

            y_conceptos -= 15
            color_actual = colors.white if color_actual == colors.whitesmoke else colors.whitesmoke

        total_pago = total_percepciones - empleado['deducciones']
        p.setFont("Helvetica-Bold", 12)
        p.drawString(cuadro_x + 200, cuadro_y - 20, f"Total a pagar: ${total_pago:,.2f}")

        firma_x = cuadro_x
        firma_y = cuadro_y - 80  
        firma_ancho = cuadro_ancho
        firma_alto = 50
        p.rect(firma_x, firma_y, firma_ancho, firma_alto)

        p.setFont("Helvetica-Bold", 10)
        p.drawString(firma_x + 10, firma_y + firma_alto - 20, "Firma del Empleado:")

        p.showPage()

    p.save()
    return response


class PeriodosNominaList(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "app.view_periodosnomina"
    model = PeriodosNomina
    template_name = 'nomina/periodos_list.html'
    context_object_name = 'periodos'
    login_url = "bases:login"

class PeriodosNominaNew(LoginRequiredMixin, generic.CreateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('periodosnomina_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)

class PeriodosNominaEdit(LoginRequiredMixin, generic.UpdateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('periodosnomina_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class PeriodosNominaDel(LoginRequiredMixin, generic.DeleteView):
    model = PeriodosNomina
    template_name = 'nomina/periodosnomina_confirm_delete.html'
    success_url = reverse_lazy('periodosnomina_list')
    login_url = 'bases:login'


def empleado_archivos(request, empleado_id):
    empleado = get_object_or_404(Empleado, id=empleado_id)
    archivos = EmpleadoArchivo.objects.filter(empleado=empleado)
    if request.method == "POST":
        form = EmpleadoArchivoForm(request.POST, request.FILES)
        if form.is_valid():
            if archivos.count() >= 5:
                return JsonResponse({"error": "Solo se pueden cargar hasta 5 archivos."}, status=400)

            archivo = form.save(commit=False)
            archivo.empleado = empleado
            archivo.save()
            return JsonResponse({"mensaje": "Archivo subido correctamente."})

    else:
        form = EmpleadoArchivoForm()

    return render(request, "empleado_archivos.html", {"empleado": empleado, "archivos": archivos, "form": form})


def eliminar_archivo(request, archivo_id):
    archivo = get_object_or_404(EmpleadoArchivo, id=archivo_id)
    empleado_id = archivo.empleado.id
    archivo.delete()
    return redirect("empleado_archivos", empleado_id=empleado_id)



class AsistenciaListView(generic.ListView):
    model = Asistencia
    template_name = "nomina/asistencia_list.html"
    context_object_name = "asistencias"
    ordering = ["-fecha"]  # Ordenar por fecha descendente

class AsistenciaDeleteView(generic.DeleteView):
    model = Asistencia
    template_name = "nomina/asistencia_confirm_delete.html"
    success_url = reverse_lazy("nom:asistencia_list") 



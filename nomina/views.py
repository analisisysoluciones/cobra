# nomina/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.views import generic
from django.views import View
from django.http import JsonResponse, HttpResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import (
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo)
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto
from .forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaDetalleProyectoForm
)
from xhtml2pdf import pisa
from django.template.loader import render_to_string, get_template
from django.contrib import messages
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Max, Q
from datetime import datetime, timedelta
from decimal import Decimal
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader



logger = logging.getLogger(__name__)


def calcular_nomina_semanal_todos(fecha_inicio_semana):
    # Convertir la fecha de inicio de la semana a objeto date si es una cadena
    if isinstance(fecha_inicio_semana, str):
        try:
            fecha_inicio_semana = datetime.strptime(fecha_inicio_semana, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Error: Formato de fecha incorrecto. Debe ser 'YYYY-MM-DD'.")
            return {'nomina': [], 'fecha_inicio': None, 'fecha_fin': None, 'total_percepciones_general': 0, 'total_deducciones_general': 0, 'total_neto_general': 0} # Retorna un diccionario vacío consistente con el retorno esperado

    # Calcular la fecha de fin de la semana (6 días después de la fecha de inicio, cubriendo 7 días en total)
    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    
    # Obtener todos los empleados activos
    empleados = Empleado.objects.filter(estado=True)
    
    nomina_lista = []
    DIAS_LABORALES_SEMANA = Decimal(6) # Definimos la constante para los días laborales esperados

    for empleado in empleados:
        logger.debug(f"Procesando empleado: {empleado.nombre}")
        
        # Contar los días registrados en Asistencia para este empleado en el rango de la semana.
        # Dado que Asistencia registra FALTAS, este count nos da directamente el número de faltas.
        dias_faltados_registrados = Asistencia.objects.filter(
            empleado=empleado,
            fecha__range=[fecha_inicio_semana, fecha_fin_semana] 
        ).count()
        
        # Aseguramos que el número de faltas no exceda los días laborales esperados
        faltas = min(dias_faltados_registrados, DIAS_LABORALES_SEMANA)

        sueldo_diario = Decimal(empleado.sueldo_diario or 0) # Asegurar que sea Decimal y no None
        compensacion = Decimal(empleado.compensacion or 0) # Asegurar que sea Decimal y no None
        
        # Días trabajados para el cálculo del sueldo semanal: Días laborales esperados - Faltas
        dias_trabajados_para_sueldo = DIAS_LABORALES_SEMANA - faltas
        sueldo_semanal = dias_trabajados_para_sueldo * sueldo_diario

        # Cálculo del Séptimo Día: Se paga el séptimo día solo si no hubo faltas (trabajó los 6 días).
        septimo_dia = sueldo_diario if faltas == 0 else Decimal(0)
        
        # Importe de las faltas: Número de faltas * sueldo diario
        importe_faltas = faltas * sueldo_diario

        # Descuento del Séptimo Día si hubo faltas.
        descuento_septimo_dia = (faltas / DIAS_LABORALES_SEMANA) * sueldo_diario if faltas > 0 else Decimal(0)
        
        logger.debug(f"Descuento séptimo día para {empleado.nombre}: {descuento_septimo_dia}")

        # Percepciones: Sueldo semanal (por días trabajados) + Séptimo Día + Compensación
        percepciones = sueldo_semanal + septimo_dia + compensacion
        
        # Deducciones: Importe de las faltas + Descuento del Séptimo Día
        deducciones = importe_faltas + descuento_septimo_dia
        
        # Total a pagar
        total_pago = percepciones - deducciones

        nomina_lista.append({
            'empleado_id': empleado.id,
            'empleado': empleado.nombre,           
            'ingreso': empleado.ingreso, # Asumo que 'ingreso' es un campo en tu modelo Empleado
            'sueldo_diario': float(sueldo_diario),
            'dias_trabajados': int(dias_trabajados_para_sueldo), # Días pagados por sueldo base
            'faltas': int(faltas), # Días de falta contados
            'importe_faltas': float(importe_faltas),
            'sueldo_semanal': float(sueldo_semanal), # Sueldo por los días efectivamente trabajados
            'septimo_dia': float(septimo_dia),
            'compensacion': float(compensacion),
            'total_pago': float(total_pago),
            'descuento_septimo_dia': float(descuento_septimo_dia),
            'percepciones': float(percepciones),
            'deducciones': float(deducciones),
        })
    
    # Calcular los totales generales para el pie de tabla
    total_percepciones_general = sum(item['percepciones'] for item in nomina_lista)
    total_deducciones_general = sum(item['deducciones'] for item in nomina_lista)
    total_neto_general = sum(item['total_pago'] for item in nomina_lista)

    logger.debug("Resultados de nómina calculados.")
    
    return {
        'nomina': nomina_lista,
        'fecha_inicio': fecha_inicio_semana,
        'fecha_fin': fecha_fin_semana,
        'total_percepciones_general': total_percepciones_general,
        'total_deducciones_general': total_deducciones_general,
        'total_neto_general': total_neto_general,
    }
#=============================================================================
# calcular nomina view
#=============================================================================

# --- Tu vista principal (modificada) ---
@login_required(login_url='bases:login')
def calcular_nomina_view(request):
    logger.debug("ENTRANDO A calcular_nomina_view")
    logger.debug(f"Session keys: {list(request.session.keys())}")
    
    # Intentamos obtener el período guardado en la sesión
    periodo_id = request.session.get('periodo_id')
    logger.debug(f"periodo_id from session: {periodo_id}")
    
    if not periodo_id:
        logger.debug("NO HAY PERIODO_ID - Redirigiendo a seleccionar_fecha")
        messages.error(request, "Debe seleccionar un período primero.")
        return redirect('nom:seleccionar_fecha')

    logger.debug("SÍ HAY PERIODO_ID - Continuando...")
    
    # Traemos el objeto período con el id de sesión
    logger.debug("Buscando periodo_obj...")
    try:
        periodo_obj = PeriodosNomina.objects.get(id=periodo_id)
        logger.debug(f"periodo_obj encontrado: {periodo_obj}")
    except PeriodosNomina.DoesNotExist: # Mejor usar la excepción específica
        logger.error(f"ERROR: El periodo con ID {periodo_id} no existe.")
        messages.error(request, "El período seleccionado no existe.")
        return redirect('nom:seleccionar_fecha')
    except Exception as e:
        logger.error(f"ERROR inesperado al buscar periodo: {e}", exc_info=True) # exc_info=True para el traceback
        messages.error(request, f"Error inesperado al cargar el período: {e}")
        return redirect('nom:seleccionar_fecha')

    logger.debug("Obteniendo fechas del periodo_obj...")
    fecha_inicio_obj = periodo_obj.periodo_inicio
    # Asegúrate de que esta fecha_inicio_obj sea un objeto date o string en el formato esperado por calcular_nomina_semanal_todos
    # Si periodo_inicio es un DateField en tu modelo, ya será un objeto date.
    logger.debug(f"Fechas del periodo_obj - Inicio: {fecha_inicio_obj}, Fin: {periodo_obj.periodo_final}")

    # Ahora llamamos a la función que calcula la nómina y obtenemos su diccionario de resultados
    logger.debug("Llamando a calcular_nomina_semanal_todos...")
    try:
        nomina_data = calcular_nomina_semanal_todos(fecha_inicio_obj)
        logger.debug(f"DESPUÉS de calcular_nomina_semanal_todos - ÉXITO. Tipo de resultado: {type(nomina_data)}")
        
        # Verifica que nomina_data sea un diccionario y tenga la clave 'nomina'
        if not isinstance(nomina_data, dict) or 'nomina' not in nomina_data:
            logger.error(f"calcular_nomina_semanal_todos retornó un formato inesperado: {nomina_data}")
            messages.error(request, "Error interno al procesar los datos de la nómina.")
            return redirect('nom:seleccionar_fecha')

    except Exception as e:
        logger.error(f"ERROR en calcular_nomina_semanal_todos: {e}", exc_info=True)
        messages.error(request, f"Error al calcular la nómina: {e}")
        return redirect('nom:seleccionar_fecha')
    
    logger.debug("Preparando contexto para el template...")
    # Creamos el contexto usando los datos devueltos por calcular_nomina_semanal_todos
    # y agregando el objeto periodo_obj
    context = {
        'nomina': nomina_data.get('nomina', []), # Si por alguna razón 'nomina' no está, que sea una lista vacía
        'fecha_inicio': nomina_data.get('fecha_inicio'),
        'fecha_fin': nomina_data.get('fecha_fin'),
        'periodo': periodo_obj, # El objeto completo del periodo
        'total_percepciones_general': nomina_data.get('total_percepciones_general', 0),
        'total_deducciones_general': nomina_data.get('total_deducciones_general', 0),
        'total_neto_general': nomina_data.get('total_neto_general', 0),
    }
    
    logger.debug("Renderizando template nomina/nomina_semanal.html")
    return render(request, 'nomina/nomina_semanal.html', context)


#================================================================================
#   **** fin calcular nomina todos ****
#================================================================================


# --- Vistas existentes y corregidas ---

class EmpleadoList(LoginRequiredMixin, generic.ListView):
    model = Empleado
    template_name = "nomina/empleado_list.html"
    context_object_name = "empleados"
    login_url = 'bases:login'

class EmpleadoNew(LoginRequiredMixin, generic.CreateView):
    model = Empleado
    template_name = "nomina/empleado_form.html"
    context_object_name = "obj"
    form_class = EmpleadoForm
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

class EmpleadoEdit(LoginRequiredMixin, generic.UpdateView):
    model = Empleado
    template_name = "nomina/empleado_form.html"
    form_class = EmpleadoForm
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

class EmpleadoDel(LoginRequiredMixin, generic.DeleteView):
    model = Empleado
    template_name = "nomina/empleado_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

@login_required(login_url='bases:login')
def DocumentoEmpleadoDelete(request, pk):
    doc = get_object_or_404(EmpleadoArchivo, pk=pk)
    empleado_pk = doc.empleado.pk
    doc.delete()
    messages.success(request, f"Documento eliminado correctamente.")
    return redirect('nom:empleado_edit', pk=empleado_pk)

@login_required(login_url='bases:login')
def capturar_falta(request):
    if request.method == 'POST':
        form = FaltaForm(request.POST)
        if form.is_valid():
            asistencia = form.save(commit=False)
            asistencia.tipo = 'F'
            asistencia.save()
            messages.success(request, 'Falta registrada exitosamente.')
            return redirect('nom:capturar_falta')
        else:
            messages.error(request, 'Error al registrar la falta. Verifique los datos.')
    else:
        form = FaltaForm()
    return render(request, 'nomina/capturar_falta.html', {'form': form})







#=================================================================
# 
# Inicio de procesa nomina
# 
#=================================================================

def procesar_nomina(request):
    if request.method == 'POST':
        print("\n--- INICIO DE PROCESAR_NOMINA (POST) ---")
        print(">>> VERSIÓN DE CÓDIGO ACTUALIZADA - JULIO 2025 <<<") # <--- AÑADE ESTA LÍNEA
        print("POST recibido:", request.POST)
        # Opcional: imprimir los datos de la sesión para depuración
        print("Periodo en sesión (para referencia):")
        print("ID:", request.session.get('periodo_id'))
        print("Semana:", request.session.get('periodo_semana'))
        print("Inicio S:", request.session.get('periodo_inicio'))
        print("Fin S:", request.session.get('periodo_final'))

        try:
            fecha_inicio_str = request.POST.get('fecha_inicio_nomina')
            fecha_fin_str = request.POST.get('fecha_fin_nomina')
            
            # Asegúrate de que las fechas se conviertan correctamente a objetos date
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            print(f"Fechas convertidas a date: Inicio={fecha_inicio}, Fin={fecha_fin}")

            # Validación: verificar si la nómina YA FUE CALCULADA/PROCESADA para el mismo periodo
            # Obtener el objeto si existe, no solo verificar si existe
            nomina_existente = NominaHistorial.objects.filter(
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                estatus='Procesada' # Mantenemos el estatus 'Procesada' aquí
            ).first() # Usa .first() para obtener el objeto o None

            if nomina_existente:
                print(f"¡ADVERTENCIA! Nómina existente encontrada (ID: {nomina_existente.id}). Redirigiendo a asignar_proyectos.")
                messages.info(request, f"La nómina para el periodo del {fecha_inicio} al {fecha_fin} ya ha sido calculada. Puedes continuar con la asignación de proyectos.")
                # AHORA nomina_existente.id está definido y se puede usar
                return redirect('nom:asignar_proyectos', nomina_id=nomina_existente.id) 
            else:
                print("No se encontró nómina existente para este período con estatus 'Procesada'. Procediendo a crearla.")

            # --- Si la nómina NO existe con estatus 'Procesada', esta sección se ejecutará ---
            empleados = Empleado.objects.filter(estado=True)
            print("Empleados activos encontrados:", empleados.count())

            if not empleados.exists():
                print("ERROR: No hay empleados activos para procesar.")
                messages.error(request, "No hay empleados activos para procesar la nómina.")
                return redirect('nom:seleccionar_fecha')

            total_general = Decimal('0.00')
            cuenta = Cuenta.objects.first()
            if not cuenta:
                print("ERROR: No hay una cuenta configurada.")
                messages.error(request, "No hay una cuenta de banco configurada para procesar la nómina.")
                return redirect('nom:seleccionar_fecha')

            # Crear encabezado de nómina
            print("Creando NominaHistorial...")
            nomina_hist = NominaHistorial.objects.create(
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                total_pago=Decimal('0.00'),
                cuenta=cuenta,
                estatus='Procesada', # O 'Calculada' si tienes un estatus intermedio
                fecha_procesada=timezone.now()
            )
            print(f"NominaHistorial creada con ID: {nomina_hist.id}")

            empleados_procesados = 0
            empleados_fallidos = []

            print("Iniciando procesamiento de detalles de nómina por empleado...")
            for emp in empleados:
                try:
                    print(f"Procesando registro de nómina para empleado: {emp.id} - {emp.nombre}")

                    sueldo_diario = emp.sueldo_diario or Decimal('0.00')
                    dias_trabajados = 6  # Esto se puede hacer dinámico más adelante
                    total_pago = sueldo_diario * dias_trabajados
                    print(f"  Sueldo diario: {sueldo_diario}, Días trabajados: {dias_trabajados}, Pago calculado: {total_pago}")

                    NominaDetalle.objects.create(
                        nomina_historica=nomina_hist,
                        empleado=emp,
                        sueldo_diario=sueldo_diario,
                        dias_trabajados=dias_trabajados,
                        total_pago=total_pago,
                        proyecto=None  # Se asignará después
                    )
                    print(f"  NominaDetalle creado para {emp.nombre}.")

                    total_general += total_pago
                    empleados_procesados += 1

                except Exception as e:
                    # Este except es para errores por empleado individual
                    print(f"❌ Error CRÍTICO al procesar empleado ID {emp.id} ({emp.nombre}): {e}")
                    messages.warning(request, f"Error al procesar empleado {emp.nombre}: {e}") # Mensaje específico para el usuario
                    empleados_fallidos.append((emp.id, str(e)))
                    # No redirigir aquí, dejar que el bucle continúe y el error general lo capture si es necesario

            print(f"Total general de pago calculado: {total_general}")
            # Actualizar total de la nómina
            nomina_hist.total_pago = total_general
            nomina_hist.save()
            print(f"NominaHistorial (ID: {nomina_hist.id}) actualizada con total_pago: {nomina_hist.total_pago}")

            messages.success(request, f"Nómina procesada correctamente. {empleados_procesados} empleados procesados.")

            if empleados_fallidos:
                messages.warning(request, f"{len(empleados_fallidos)} empleados no fueron procesados.")
                for emp_id, error in empleados_fallidos:
                    print(f"Empleado con error: ID {emp_id}, Motivo: {error}")

            print(f"Redirigiendo a 'nom:asignar_proyectos' con nomina_id={nomina_hist.id}")
            return redirect('nom:asignar_proyectos', nomina_id=nomina_hist.id)

        except Exception as e:
            messages.error(request, f"Ocurrió un error al procesar la nómina: {e}")
            print(f"--- ERROR GENERAL EN PROCESAR_NOMINA (OUTER EXCEPT): {e} ---")
            traceback.print_exc() # Esto imprimirá la traza completa del error
            return redirect('nom:seleccionar_fecha')

    print("\n--- FIN DE PROCESAR_NOMINA (NO POST) ---")
    return redirect('nom:seleccionar_fecha')

#=================================================================
# 
# fin de procesa nomina
# 
#=================================================================
    





@login_required(login_url='bases:login')
def listar_detalles_nomina_procesada(request, nomina_historial_id):
    """
    Vista para listar los detalles de una nómina histórica específica.
    """
    nomina_historial = get_object_or_404(NominaHistorial, id=nomina_historial_id)
    detalles_nomina = NominaDetalle.objects.filter(nomina_historica=nomina_historial).order_by('empleado__nombre')

    context = {
        'nomina_historial': nomina_historial,
        'detalles_nomina': detalles_nomina,
    }
    return render(request, 'nomina/detalles_nomina_procesada.html', context)

@login_required(login_url='bases:login')
def asignar_proyecto_individual(request, detalle_id):
    detalle = get_object_or_404(NominaDetalle, id=detalle_id)

    if not detalle.nomina_historica:
        messages.error(request, "El detalle de nómina no está asociado a un historial válido.")
        return redirect('nom:seleccionar_fecha')

    nomina_historial_id = detalle.nomina_historica.id

    if request.method == "POST":
        form = AsignarProyectoForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Proyecto asignado a {detalle.empleado.nombre} correctamente.")
            return redirect('nom:listar_detalles_nomina_procesada', nomina_historial_id=nomina_historial_id)
        else:
            messages.error(request, "Error al asignar el proyecto. Verifique los datos.")
    else:
        form = AsignarProyectoForm(instance=detalle)

    context = {
        'form': form,
        'detalle': detalle,
        'nomina_historial_id': nomina_historial_id,
    }
    return render(request, 'nomina/asignar_proyecto.html', context)

# --- Funciones para PDF ---

def formato_fecha(fecha):
    return fecha.strftime("%d-%B-%Y").capitalize()



@login_required(login_url='bases:login')
def generar_nomina_pdf(request, fecha_str):
    """
    Genera PDF de nómina semanal con layout mejorado y sin superposiciones
    """
    # 1. Obtener las fechas correctas del período
    try:
        fecha_inicio_semana = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha en la URL incorrecto.")
        return redirect('nom:seleccionar_fecha')

    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)

    # 2. Llamar a la función de cálculo de nómina
    resultados_calculo = calcular_nomina_semanal_todos(fecha_inicio_semana.strftime("%Y-%m-%d"))

    # 3. Extraer la lista de datos de nómina del diccionario devuelto
    if not isinstance(resultados_calculo, dict) or 'nomina' not in resultados_calculo:
        messages.error(request, "Formato de datos de nómina inesperado de la función de cálculo. Contacte al administrador.")
        return redirect('nom:seleccionar_fecha')

    nomina_data = resultados_calculo['nomina']

    # 4. Verificar si hay datos de nómina para procesar
    if not nomina_data:
        messages.info(request, "No hay datos de nómina para generar el PDF en el período seleccionado.")
        return redirect('nom:seleccionar_fecha')

    # --- Configuración inicial del PDF ---
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="nomina_semanal_{fecha_str}.pdf"'

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(legal))

    # Dimensiones de página
    ancho_pagina = landscape(legal)[0]  # 1008 points
    alto_pagina = landscape(legal)[1]   # 612 points
    margen_izquierdo = 30
    margen_derecho = 30
    margen_superior = 50
    margen_inferior = 80  # Más espacio para el pie de página
    ancho_util = ancho_pagina - margen_izquierdo - margen_derecho

    print(f"DEBUG: Dimensiones - Ancho: {ancho_pagina}, Alto: {alto_pagina}, Ancho útil: {ancho_util}")

    # --- ENCABEZADO ---
    def dibujar_encabezado():
        # Posición Y inicial del encabezado (desde arriba)
        header_y = alto_pagina - margen_superior
        
        # Logo
        logo_path = "static/base/img/inemo.png"
        logo_width = 100
        logo_height = 50
        
        try:
            logo = ImageReader(logo_path)
            p.drawImage(logo, margen_izquierdo, header_y - logo_height, 
                       width=logo_width, height=logo_height, mask="auto")
            print(f"DEBUG: Logo dibujado en Y: {header_y - logo_height}")
        except Exception as e:
            print(f"⚠ No se pudo cargar el logo: {e}")

        # Texto del encabezado
        text_x = margen_izquierdo + logo_width + 15
        
        # Título
        try:
            titulo = f"Reporte de Nómina del {formato_fecha(fecha_inicio_semana)} al {formato_fecha(fecha_fin_semana)}"
        except NameError:
            titulo = f"Reporte de Nómina del {fecha_inicio_semana.strftime('%d-%B-%Y')} al {fecha_fin_semana.strftime('%d-%B-%Y')}"

        p.setFont("Helvetica-Bold", 12)
        p.drawString(text_x, header_y - 15, titulo)
        
        p.setFont("Helvetica", 10)
        p.drawString(text_x, header_y - 30, "Domicilio: Puerto Altata 590")
        p.drawString(text_x, header_y - 45, "RFC: IEM060621IE3")
        
        # Retorna la posición Y donde termina el encabezado
        return header_y - 60

    header_end_y = dibujar_encabezado()

    # --- PREPARACIÓN DE DATOS DE LA TABLA ---
    # Encabezados principales y subtítulos
    encabezados = ["Nombre del Empleado", "Percepciones", "", "", "", "", "", "Deducciones", "", "", "", "Total", "Firma"]
    subtitulos = ["", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", ""]

    # Inicializar totales
    totales = {
        "03": Decimal('0.0'),
        "04": Decimal('0.0'), 
        "06": Decimal('0.0'),
        "08": Decimal('0.0'),
        "09": Decimal('0.0'),
        "10": Decimal('0.0'),
        "11": Decimal('0.0')
    }

    # Preparar datos de empleados
    datos_empleados = []
    for item in nomina_data:
        fila = [
            item.get("empleado", ""),
            f"${item.get('sueldo_diario', 0):.2f}",
            str(item.get("dias_trabajados", 0)),
            f"${item.get('sueldo_semanal', 0):.2f}",
            f"${item.get('septimo_dia', 0):.2f}",
            f"${item.get('compensacion', 0):.2f}",
            f"${item.get('percepciones', 0):.2f}",
            str(item.get("faltas", 0)),
            f"${item.get('importe_faltas', 0):.2f}",
            f"${item.get('descuento_septimo_dia', 0):.2f}",
            f"${item.get('deducciones', 0):.2f}",
            f"${item.get('total_pago', 0):.2f}",
            ""
        ]
        
        # Acumular totales
        totales["03"] += Decimal(str(item.get('sueldo_semanal', 0)))
        totales["04"] += Decimal(str(item.get('septimo_dia', 0)))
        totales["06"] += Decimal(str(item.get('percepciones', 0)))
        totales["08"] += Decimal(str(item.get('importe_faltas', 0)))
        totales["09"] += Decimal(str(item.get('descuento_septimo_dia', 0)))
        totales["10"] += Decimal(str(item.get('deducciones', 0)))
        totales["11"] += Decimal(str(item.get('total_pago', 0)))
        
        datos_empleados.append(fila)

    # Fila de totales
    fila_totales = [
        "TOTAL",
        "", "", f"${totales['03']:.2f}", f"${totales['04']:.2f}", "", f"${totales['06']:.2f}", "",
        f"${totales['08']:.2f}", f"${totales['09']:.2f}", f"${totales['10']:.2f}", f"${totales['11']:.2f}", ""
    ]

    # Combinar todos los datos
    datos_tabla = [encabezados, subtitulos] + datos_empleados + [fila_totales]

    # --- CONFIGURACIÓN DE LA TABLA ---
    # Anchos de columna optimizados para landscape legal
    col_widths = [170, 50, 35, 65, 65, 65, 65, 35, 65, 65, 65, 65, 100]
    
    # Verificar que el ancho total no exceda el disponible
    ancho_total_tabla = sum(col_widths)
    if ancho_total_tabla > ancho_util:
        factor_escala = ancho_util / ancho_total_tabla * 0.95  # 5% de margen
        col_widths = [w * factor_escala for w in col_widths]
        print(f"DEBUG: Tabla escalada por factor {factor_escala:.3f}")

    # Alturas de fila
    row_heights = [25, 20] + [18] * len(datos_empleados) + [22]  # Encabezados más altos

    # Crear tabla
    tabla = Table(datos_tabla, colWidths=col_widths, rowHeights=row_heights)

    # --- ESTILOS DE LA TABLA ---
    estilos = TableStyle([
        # Encabezados principales
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        
        # Subtítulos
        ("BACKGROUND", (0, 1), (-1, 1), colors.lightgrey),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 8),
        
        # Datos generales
        ("FONTNAME", (0, 2), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 2), (-1, -2), 7),
        
        # Fila de totales
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 8),
        
        # Alineaciones
        ("ALIGN", (1, 0), (-2, -1), "CENTER"),  # Todas las columnas numéricas centradas
        ("ALIGN", (0, 0), (0, -1), "LEFT"),     # Columna de nombres a la izquierda
        ("ALIGN", (-1, 0), (-1, -1), "CENTER"), # Columna de firma centrada
        
        # Alineación de números a la derecha para mejor lectura
        ("ALIGN", (1, 2), (11, -1), "RIGHT"),
        
        # Alineación vertical
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        
        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        
        # Spans para encabezados agrupados
        ("SPAN", (1, 0), (6, 0)),   # "Percepciones"
        ("SPAN", (7, 0), (10, 0)),  # "Deducciones"
        ("SPAN", (11, 0), (11, 0)), # "Total"
        ("SPAN", (12, 0), (12, 0)), # "Firma"
    ])

    # Alternar colores de filas para mejor legibilidad
    for i in range(2, len(datos_tabla) - 1):
        if i % 2 == 0:
            estilos.add("BACKGROUND", (0, i), (-1, i), colors.whitesmoke)

    tabla.setStyle(estilos)

    # --- POSICIONAMIENTO Y DIBUJO DE LA TABLA ---
    # Calcular espacio disponible para la tabla
    espacio_disponible = header_end_y - margen_inferior
    ancho_tabla, alto_tabla = tabla.wrapOn(p, ancho_util, espacio_disponible)
    
    print(f"DEBUG: Espacio disponible: {espacio_disponible}, Alto tabla: {alto_tabla}")
    
    # Verificar si la tabla cabe en la página
    if alto_tabla > espacio_disponible:
        print("ADVERTENCIA: La tabla es muy alta para la página")
        # Reducir altura de filas si es necesario
        row_heights = [20, 16] + [14] * len(datos_empleados) + [18]
        tabla = Table(datos_tabla, colWidths=col_widths, rowHeights=row_heights)
        tabla.setStyle(estilos)
        ancho_tabla, alto_tabla = tabla.wrapOn(p, ancho_util, espacio_disponible)

    # Posición Y para dibujar la tabla (esquina inferior izquierda)
    table_y = header_end_y - alto_tabla - 20  # 20 puntos de separación del encabezado
    
    # Asegurar que no se superponga con el pie de página
    if table_y < margen_inferior:
        table_y = margen_inferior
        print(f"DEBUG: Tabla ajustada para evitar superposición con pie de página")

    # Dibujar la tabla
    tabla.drawOn(p, margen_izquierdo, table_y)
    print(f"DEBUG: Tabla dibujada en X: {margen_izquierdo}, Y: {table_y}")

    # --- PIE DE PÁGINA ---
    def dibujar_pie_pagina():
        pie_texto = (
            "01.- Sueldo diario, 02.- Días trabajados, 03.- Importe días trabajados, "
            "04.- Pago 7mo día, 05.- Compensación, 06.- Total percepciones, "
            "07.- Faltas, 08.- Descuento por falta, 09.- Proporcional 7mo día, "
            "10.- Total deducciones, 11.- Pago neto."
        )
        
        p.setFont("Helvetica", 7)
        
        # Dividir el texto en líneas si es muy largo
        max_width = ancho_util
        words = pie_texto.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if p.stringWidth(test_line, "Helvetica", 7) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Dibujar líneas del pie de página
        y_pos = 40
        for line in lines:
            p.drawString(margen_izquierdo, y_pos, line)
            y_pos -= 10

    dibujar_pie_pagina()

    # Finalizar PDF
    p.save()
    buffer.seek(0)
    response.write(buffer.read())
    return response


LOGO_PATH = "static/base/img/inemo.png"

@login_required(login_url='bases:login')
def generar_nomina_individual_pdf(request, fecha_str):
    """
    Genera PDF de recibos de nómina individuales con layout mejorado
    """
    # 1. Obtener las fechas correctas del período
    try:
        fecha_inicio_semana = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha en la URL incorrecto.")
        return redirect('nom:seleccionar_fecha')

    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)

    # 2. Llamar a la función de cálculo de nómina
    resultados_calculo = calcular_nomina_semanal_todos(fecha_inicio_semana.strftime("%Y-%m-%d"))

    # 3. Extraer la lista de datos de nómina del diccionario devuelto
    if not isinstance(resultados_calculo, dict) or 'nomina' not in resultados_calculo:
        messages.error(request, "Formato de datos de nómina inesperado de la función de cálculo. Contacte al administrador.")
        return redirect('nom:seleccionar_fecha')

    nomina_data = resultados_calculo['nomina']

    # 4. Verificar si hay datos de nómina para procesar
    if not nomina_data:
        messages.info(request, "No hay datos de nómina para generar el PDF en el período seleccionado.")
        return redirect('nom:seleccionar_fecha')

    # --- Configuración inicial del PDF ---
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="nomina_individual_{fecha_str}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter  # 612 x 792 points
    
    # Márgenes
    margen_izq = 40
    margen_der = 40
    margen_sup = 50
    margen_inf = 50
    ancho_util = width - margen_izq - margen_der

    print(f"DEBUG Individual: Dimensiones - Ancho: {width}, Alto: {height}, Ancho útil: {ancho_util}")

    # --- Función para dibujar encabezado ---
    def dibujar_encabezado_empleado(empleado_data):
        """Dibuja el encabezado para cada empleado"""
        # Posición Y inicial del encabezado (desde arriba)
        header_y = height - margen_sup
        
        # Logo
        logo_width = 100
        logo_height = 50
        
        try:
            p.drawImage(LOGO_PATH, margen_izq, header_y - logo_height, 
                       width=logo_width, height=logo_height)
            print(f"DEBUG: Logo dibujado en Y: {header_y - logo_height}")
        except Exception as e:
            p.setFillColor(colors.red)
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margen_izq, header_y - 30, "LOGO NO ENCONTRADO")
            p.setFillColor(colors.black)
            print(f"⚠ No se pudo cargar el logo: {e}")

        # Información de la empresa
        text_x = margen_izq + logo_width + 20
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(text_x, header_y - 20, "Recibo de Nómina")
        
        # Período
        try:
            periodo_texto = f"Período: {formato_fecha(fecha_inicio_semana)} al {formato_fecha(fecha_fin_semana)}"
        except NameError:
            periodo_texto = f"Período: {fecha_inicio_semana.strftime('%d/%m/%Y')} al {fecha_fin_semana.strftime('%d/%m/%Y')}"
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(text_x, header_y - 38, periodo_texto)
        
        p.setFont("Helvetica", 9)
        p.drawString(text_x, header_y - 52, "Domicilio: Puerto Altata 590")
        p.drawString(text_x, header_y - 65, "RFC: IEM060621IE3")
        
        # Información del empleado
        p.setFont("Helvetica-Bold", 14)
        empleado_y = header_y - 90
        p.drawString(margen_izq, empleado_y, f"Empleado: {empleado_data.get('empleado', 'N/A')}")
        
        # Fecha de ingreso
        p.setFont("Helvetica", 11)
        fecha_ingreso = empleado_data.get('ingreso', 'N/A')
        if fecha_ingreso != 'N/A':
            try:
                if hasattr(fecha_ingreso, 'strftime'):
                    fecha_ingreso_str = fecha_ingreso.strftime('%d/%m/%Y')
                else:
                    fecha_ingreso_str = str(fecha_ingreso)
            except:
                fecha_ingreso_str = 'N/A'
        else:
            fecha_ingreso_str = 'N/A'
            
        p.drawString(margen_izq, empleado_y - 20, f"Fecha de Ingreso: {fecha_ingreso_str}")
        
        # Retorna la posición Y donde termina el encabezado
        return empleado_y - 45

    # --- Función para dibujar el detalle de nómina ---
    def dibujar_detalle_nomina(empleado_data, start_y):
        """Dibuja el detalle de percepciones y deducciones"""
        
        # Calcular valores
        compensacion = empleado_data.get('compensacion', 0)
        importe_dias_trabajados = empleado_data.get('sueldo_semanal', 0)  # Ya viene calculado
        
        # Dimensiones del cuadro principal
        cuadro_x = margen_izq
        cuadro_ancho = ancho_util
        cuadro_alto = 200
        cuadro_y = start_y - cuadro_alto - 20  # 20 puntos de separación
        
        # Verificar que el cuadro no se salga de la página
        if cuadro_y < margen_inf + 100:  # Dejar espacio para firma y total
            print("ADVERTENCIA: El cuadro principal se ajustó por espacio")
            cuadro_y = margen_inf + 100
            cuadro_alto = start_y - cuadro_y - 20
        
        # Dibujar cuadro principal
        p.setStrokeColor(colors.black)
        p.setLineWidth(1)
        p.rect(cuadro_x, cuadro_y, cuadro_ancho, cuadro_alto)
        
        # Línea divisoria vertical (centro)
        centro_x = cuadro_x + (cuadro_ancho / 2)
        p.line(centro_x, cuadro_y, centro_x, cuadro_y + cuadro_alto)
        
        # --- SECCIÓN PERCEPCIONES ---
        p.setFont("Helvetica-Bold", 12)
        p.drawString(cuadro_x + 15, cuadro_y + cuadro_alto - 25, "PERCEPCIONES")
        
        percepciones = [
            ("Sueldo Diario:", empleado_data.get('sueldo_diario', 0)),
            ("Días Trabajados:", empleado_data.get('dias_trabajados', 0)),
            ("Importe Días Trabajados:", importe_dias_trabajados),
            ("Séptimo Día:", empleado_data.get('septimo_dia', 0)),
            ("Compensación:", compensacion),
        ]
        
        total_percepciones = (
            importe_dias_trabajados + 
            empleado_data.get('septimo_dia', 0) + 
            compensacion
        )
        
        y_pos = cuadro_y + cuadro_alto - 50
        p.setFont("Helvetica", 10)
        
        for i, (concepto, valor) in enumerate(percepciones):
            # Color alternado para mejor legibilidad
            if i % 2 == 0:
                p.setFillColor(colors.whitesmoke)
                p.rect(cuadro_x + 5, y_pos - 3, centro_x - cuadro_x - 15, 16, fill=1, stroke=0)
            
            p.setFillColor(colors.black)
            
            if concepto == "Días Trabajados:":
                texto = f"{concepto} {int(valor)}"
            else:
                texto = f"{concepto} ${valor:,.2f}"
            
            p.drawString(cuadro_x + 10, y_pos, texto)
            y_pos -= 18
        
        # Total percepciones
        p.setFillColor(colors.lightgrey)
        p.rect(cuadro_x + 5, y_pos - 3, centro_x - cuadro_x - 15, 18, fill=1, stroke=0)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(cuadro_x + 10, y_pos, f"TOTAL PERCEPCIONES: ${total_percepciones:,.2f}")
        
        # --- SECCIÓN DEDUCCIONES ---
        p.setFont("Helvetica-Bold", 12)
        p.drawString(centro_x + 15, cuadro_y + cuadro_alto - 25, "DEDUCCIONES")
        
        deducciones = [
            ("Faltas:", empleado_data.get('faltas', 0)),
            ("Descuento por falta:", empleado_data.get('importe_faltas', 0)),
            ("Descuento 7mo día:", empleado_data.get('descuento_septimo_dia', 0)),
        ]
        
        total_deducciones = empleado_data.get('deducciones', 0)
        
        y_pos = cuadro_y + cuadro_alto - 50
        p.setFont("Helvetica", 10)
        
        for i, (concepto, valor) in enumerate(deducciones):
            # Color alternado
            if i % 2 == 0:
                p.setFillColor(colors.whitesmoke)
                p.rect(centro_x + 5, y_pos - 3, cuadro_ancho - (centro_x - cuadro_x) - 15, 16, fill=1, stroke=0)
            
            p.setFillColor(colors.black)
            
            if concepto == "Faltas:":
                texto = f"{concepto} {int(valor)}"
            else:
                texto = f"{concepto} ${valor:,.2f}"
            
            p.drawString(centro_x + 10, y_pos, texto)
            y_pos -= 18
        
        # Total deducciones
        p.setFillColor(colors.lightgrey)
        p.rect(centro_x + 5, y_pos - 3, cuadro_ancho - (centro_x - cuadro_x) - 15, 18, fill=1, stroke=0)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(centro_x + 10, y_pos, f"TOTAL DEDUCCIONES: ${total_deducciones:,.2f}")
        
        return cuadro_y  # Retorna donde termina el cuadro
    
    # --- Función para dibujar total y firma ---
    def dibujar_total_y_firma(empleado_data, start_y):
        """Dibuja el total a pagar y la sección de firma"""
        
        # Calcular total a pagar
        total_percepciones = (
            empleado_data.get('sueldo_semanal', 0) + 
            empleado_data.get('septimo_dia', 0) + 
            empleado_data.get('compensacion', 0)
        )
        total_deducciones = empleado_data.get('deducciones', 0)
        total_pago = total_percepciones - total_deducciones
        
        # Total a pagar
        total_y = start_y - 40
        p.setFont("Helvetica-Bold", 16)
        p.setFillColor(colors.darkblue)
        
        # Fondo para el total
        p.setFillColor(colors.lightblue)
        p.rect(margen_izq, total_y - 5, ancho_util, 25, fill=1, stroke=1)
        
        p.setFillColor(colors.darkblue)
        texto_total = f"TOTAL A PAGAR: ${total_pago:,.2f}"
        text_width = p.stringWidth(texto_total, "Helvetica-Bold", 16)
        x_centrado = margen_izq + (ancho_util - text_width) / 2
        p.drawString(x_centrado, total_y, texto_total)
        
        # Sección de firma
        firma_y = total_y - 70
        firma_alto = 60
        
        # Verificar espacio disponible
        if firma_y < margen_inf:
            firma_y = margen_inf
            firma_alto = total_y - 30 - margen_inf
        
        p.setFillColor(colors.black)
        p.setStrokeColor(colors.black)
        p.rect(margen_izq, firma_y, ancho_util, firma_alto)
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(margen_izq + 15, firma_y + firma_alto - 20, "Firma del Empleado:")
        
        # Línea para la firma
        p.line(margen_izq + 200, firma_y + 15, margen_izq + ancho_util - 20, firma_y + 15)
    
    # --- Generar página para cada empleado ---
    for i, empleado in enumerate(nomina_data):
        print(f"DEBUG: Procesando empleado {i+1}: {empleado.get('empleado', 'N/A')}")
        
        # Dibujar encabezado
        header_end_y = dibujar_encabezado_empleado(empleado)
        
        # Dibujar detalle de nómina
        detail_end_y = dibujar_detalle_nomina(empleado, header_end_y)
        
        # Dibujar total y firma
        dibujar_total_y_firma(empleado, detail_end_y)
        
        # Nueva página para el siguiente empleado (excepto el último)
        if i < len(nomina_data) - 1:
            p.showPage()
    
    # Finalizar PDF
    p.save()
    return response
# --- Vistas de períodos ---

class PeriodosNominaList(LoginRequiredMixin, generic.ListView):
    model = PeriodosNomina
    template_name = "nomina/periodos_list.html"
    context_object_name = "periodos"
    login_url = 'bases:login'

class PeriodosNominaNew(LoginRequiredMixin, generic.CreateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('nom:periodos_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)

class PeriodosNominaEdit(LoginRequiredMixin, generic.UpdateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('nom:periodos_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class PeriodosNominaDel(LoginRequiredMixin, generic.DeleteView):
    model = PeriodosNomina
    template_name = "nomina/periodos_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:periodos_list")
    login_url = "bases:login"

@login_required(login_url='bases:login')
def validar_curp(request):
    curp = request.GET.get('curp', None)
    data = {
        'is_taken': Empleado.objects.filter(curp__iexact=curp).exists()
    }
    return JsonResponse(data)

# --- Vistas de Asistencia ---

class AsistenciaListView(LoginRequiredMixin, generic.ListView):
    model = Asistencia
    template_name = "nomina/asistencia_list.html"
    context_object_name = "obj"
    login_url = 'bases:login'

class AsistenciaDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Asistencia
    template_name = "nomina/asistencia_confirm_delete.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:asistencia_list")
    login_url = "bases:login"





def seleccionar_periodo(request):
    periodos = PeriodosNomina.objects.all().order_by('-periodo_inicio')
    periodo_id = request.session.get('periodo_id')

    print("TOTAL PERIODOS:", periodos.count())  # <- Esto te ayuda a depurar

    return render(request, 'nomina/periodo_semanal.html', {
        'periodos': periodos,
        'periodo_id': periodo_id,
    })





# Agrega estos prints en seleccionar_periodo_nomina:

# 1. Agrega estos prints en seleccionar_periodo_nomina:

@login_required(login_url='bases:login')
def seleccionar_periodo_nomina(request):
    print("🔍 DEBUG: Entrando a seleccionar_periodo_nomina")
    print(f"🔍 DEBUG: Método: {request.method}")
    
    if request.method == 'POST':
        print("🔍 DEBUG: Es POST")
        form = SeleccionarPeriodoForm(request.POST)
        print(f"🔍 DEBUG: Form data: {request.POST}")
        
        if form.is_valid():
            print("🔍 DEBUG: Form es válido")
            periodo = form.cleaned_data['periodo']
            print(f"🔍 DEBUG: Periodo seleccionado: {periodo}")

            # Guardar los datos en la sesión
            request.session['periodo_id'] = periodo.id
            request.session['periodo_semana'] = periodo.semana
            request.session['periodo_inicio'] = str(periodo.periodo_inicio)
            request.session['periodo_final'] = str(periodo.periodo_final)
            
            print(f"🔍 DEBUG: Datos guardados en session: {request.session.get('periodo_id')}")
            print("🔍 DEBUG Antes del redirect - Session keys:", list(request.session.keys()))
            print("🔍 DEBUG: Haciendo redirect a nom:calcular_nomina")

            return redirect('nom:calcular_nomina')
        else:
            print(f"🔍 DEBUG: Form NO es válido. Errores: {form.errors}")
    else:
        print("🔍 DEBUG: Es GET, creando form vacío")
        form = SeleccionarPeriodoForm()

    print("🔍 DEBUG: Renderizando template seleccionar_fecha.html")
    return render(request, 'nomina/seleccionar_fecha.html', {'form': form})


@login_required(login_url='bases:login')
def seleccionar_periodo_nomina(request):
    print("🔍 DEBUG: Entrando a seleccionar_periodo_nomina")
    print(f"🔍 DEBUG: Método: {request.method}")
    
    if request.method == 'POST':
        print("🔍 DEBUG: Es POST")
        form = SeleccionarPeriodoForm(request.POST)
        print(f"🔍 DEBUG: Form data: {request.POST}")
        
        if form.is_valid():
            print("🔍 DEBUG: Form es válido")
            periodo = form.cleaned_data['periodo']
            print(f"🔍 DEBUG: Periodo seleccionado: {periodo}")

            # Guardar los datos en la sesión
            request.session['periodo_id'] = periodo.id
            request.session['periodo_semana'] = periodo.semana
            request.session['periodo_inicio'] = str(periodo.periodo_inicio)
            request.session['periodo_final'] = str(periodo.periodo_final)
            
            print(f"🔍 DEBUG: Datos guardados en session: {request.session.get('periodo_id')}")
            print("🔍 DEBUG: Haciendo redirect a nom:calcular_nomina")

            return redirect('nom:calcular_nomina')
        else:
            print(f"🔍 DEBUG: Form NO es válido. Errores: {form.errors}")
    else:
        print("🔍 DEBUG: Es GET, creando form vacío")
        form = SeleccionarPeriodoForm()

    print("🔍 DEBUG: Renderizando template seleccionar_fecha.html")
    return render(request, 'nomina/seleccionar_fecha.html', {'form': form})

def procesar_nomina_form(request):
    periodo_id = request.session.get('periodo_id')
    periodo_semana = request.session.get('periodo_semana')
    fecha_inicio = request.session.get('periodo_inicio')
    fecha_fin = request.session.get('periodo_final')

    if not periodo_id:
        messages.error(request, "Primero seleccione un período.")
        return redirect('nom:seleccionar_fecha')

    context = {
        'periodo_id': periodo_id,
        'semana': periodo_semana,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    return render(request, 'nomina/procesar_nomina.html', context)


class NominaDetalleListView(generic.ListView):
    model = NominaDetalle
    template_name = 'nomina/asignar_proyectos.html'
    context_object_name = 'detalles'

    def get_queryset(self):
        return NominaDetalle.objects.filter(nomina_historica_id=self.kwargs['nomina_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nomina_id'] = self.kwargs['nomina_id']
        return context


class NominaDetalleUpdateView(generic.UpdateView):
    model = NominaDetalle
    form_class = NominaDetalleProyectoForm
    template_name = 'nomina/editar_proyecto.html'

    def get_success_url(self):
        return reverse_lazy('nom:asignar_proyecto', kwargs={
            'nomina_id': self.object.nomina_historica_id
        })




def asignar_proyectos(request, nomina_id):
    print(f"DEBUG: *** Entrando a asignar_proyectos para nomina ID: {nomina_id} ***")
    
    nomina = get_object_or_404(NominaHistorial, id=nomina_id)
    print(f"DEBUG: Nómina Historial obtenida: {nomina.id}, Periodo: {nomina.periodo_inicio} - {nomina.periodo_fin}")
    
    detalles = NominaDetalle.objects.filter(nomina_historica=nomina).select_related('empleado', 'proyecto')
    print(f"DEBUG: Detalles de nómina encontrados: {detalles.count()}")
    
    # Imprime un detalle para verificar sus propiedades
    if detalles.exists():
        first_detalle = detalles.first()
        print(f"DEBUG: Primer detalle - ID: {first_detalle.id}, Empleado: {first_detalle.empleado.nombre}, Proyecto actual: {first_detalle.proyecto}")
    else:
        print("DEBUG: No se encontraron detalles de nómina para esta nómina.")

    proyectos = Proyecto.objects.all().order_by('nombre')
    print(f"DEBUG: Proyectos disponibles: {proyectos.count()}")

    if request.method == "POST":
        print("DEBUG: Procesando POST para asignación de proyectos...")
        updated_count = 0
        errors_count = 0
        try:
            with transaction.atomic():
                for key, value in request.POST.items():
                    if key.startswith("proyecto_"):
                        try:
                            detalle_id = int(key.split("_")[1])
                            proyecto_id = int(value)
                            detalle = NominaDetalle.objects.get(id=detalle_id, nomina_historica=nomina)
                            
                            if proyecto_id == 0 or value == '': # Asume 0 o cadena vacía para desasignar
                                detalle.proyecto = None
                            else:
                                proyecto = Proyecto.objects.get(id=proyecto_id)
                                detalle.proyecto = proyecto
                            
                            detalle.save()
                            updated_count += 1
                        except (NominaDetalle.DoesNotExist, Proyecto.DoesNotExist, ValueError) as e:
                            errors_count += 1
                            print(f"DEBUG: ERROR al asignar proyecto al detalle {detalle_id}: {e}")
                            messages.warning(request, f"No se pudo asignar proyecto al detalle ID {detalle_id}: {e}") # Mostrar errores individuales
                            continue 
                if updated_count > 0:
                    messages.success(request, f"Se asignaron proyectos a {updated_count} detalles de nómina.")
                if errors_count > 0:
                    messages.warning(request, f"Hubo {errors_count} errores al intentar asignar proyectos. Revisa los detalles.")
                
                print(f"DEBUG: Redirigiendo a nom:asignar_proyectos con nomina_id={nomina.id}")
                return redirect('nom:asignar_proyectos', nomina_id=nomina.id)
        except Exception as e:
            messages.error(request, f"Ocurrió un error inesperado al guardar las asignaciones: {e}")
            print(f"DEBUG: ERROR General en POST de asignar_proyectos: {e}")
            return redirect('nom:asignar_proyectos', nomina_id=nomina.id)

    print("DEBUG: Renderizando template nomina/asignar_proyectos.html")
    return render(request, 'nomina/asignar_proyectos.html', {
        'nomina': nomina,
        'detalles': detalles,
        'proyectos': proyectos,
    })

# Asegúrate de que esta vista esté definida si la usas
class NominaDetalleUpdateView(generic.UpdateView):
    # ... tu código actual ...
    def get_success_url(self):
        nomina_historial_id = self.object.nomina_historica.id 
        messages.success(self.request, "Proyecto asignado correctamente.")
        print(f"DEBUG: Redirigiendo desde NominaDetalleUpdateView a nom:asignar_proyectos con nomina_id={nomina_historial_id}")
        return reverse_lazy('nom:asignar_proyectos', kwargs={'nomina_id': nomina_historial_id})



@login_required
def cerrar_nomina(request, nomina_id):
    if request.method == 'POST':
        nomina = get_object_or_404(NominaHistorial, pk=nomina_id)
        try:
            # Aquí puedes añadir más validaciones si es necesario
            if nomina.estatus == 'Procesada':
                messages.error(request, "Esta nómina ya está procesada y no puede ser cerrada de nuevo.")
            else:
                nomina.estatus = 'Procesada' # O 'Cerrada', si añades ese estatus a tu modelo
                # Si 'Procesada' ya establece la fecha en el save del modelo, no la repitas aquí
                nomina.save()
                messages.success(request, f"La nómina del período {nomina.periodo_inicio} ha sido cerrada exitosamente.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error al cerrar la nómina: {e}")
    return redirect('nom:seleccionar_fecha') # Redirige a donde consideres apropiado



def procesar_nomina_form(request):
    periodo_id = request.session.get('periodo_id')
    periodo_semana = request.session.get('periodo_semana')
    fecha_inicio = request.session.get('periodo_inicio')
    fecha_fin = request.session.get('periodo_final')

    if not periodo_id:
        messages.error(request, "Primero seleccione un período.")
        return redirect('nom:seleccionar_fecha')

    context = {
        'periodo_id': periodo_id,
        'semana': periodo_semana,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    return render(request, 'nomina/procesar_nomina.html', context)



@login_required(login_url='bases:login')
def cerrar_nomina(request):
    logger.debug("--- INICIO DE CERRAR_NOMINA ---")

    if request.method == 'POST':
        logger.debug("Método: POST")
        nomina_historial_id = request.POST.get('nomina_historial_id')

        if not nomina_historial_id:
            logger.error("ERROR: No se recibió nomina_historial_id en la solicitud POST.")
            messages.error(request, "No se pudo identificar la nómina a cerrar. Intente de nuevo.")
            return redirect('nom:seleccionar_fecha')

        try:
            nomina_historial = get_object_or_404(NominaHistorial, pk=nomina_historial_id)
            logger.debug(f"NominaHistorial encontrada: ID {nomina_historial.id}, Estatus actual: {nomina_historial.estatus}")

            if nomina_historial.estatus == 'Procesada':
                logger.info(f"Nómina ID {nomina_historial.id} ya está procesada. Redirigiendo.")
                messages.info(
                    request,
                    f"La nómina de la semana {nomina_historial.periodo_nomina.semana} "
                    f"({nomina_historial.periodo_nomina.periodo_inicio} al {nomina_historial.periodo_nomina.periodo_final}) "
                    f"ya ha sido cerrada."
                )
                return redirect('nom:nominas_cerradas_list')

            with transaction.atomic():
                total_descontado_de_cuentas = Decimal('0.00')
                detalles_nomina = NominaDetalle.objects.filter(nomina_historica=nomina_historial)
                logger.debug(f"Procesando {detalles_nomina.count()} detalles de nómina.")

                if not detalles_nomina.exists():
                    logger.warning(f"No hay detalles de nómina para NominaHistorial ID {nomina_historial.id}.")
                    messages.warning(request, "No se encontraron detalles de empleados para esta nómina. No se realizaron descuentos de cuentas.")
                    
                    nomina_historial.estatus = 'Procesada'
                    nomina_historial.fecha_procesada = timezone.now()
                    nomina_historial.save()
                    
                    messages.success(
                        request,
                        f"Nómina semana {nomina_historial.periodo_nomina.semana} "
                        f"({nomina_historial.periodo_nomina.periodo_inicio} al {nomina_historial.periodo_nomina.periodo_final}) "
                        f"marcada como procesada (sin descuentos)."
                    )
                    return redirect('nom:nominas_cerradas_list')

                for detalle in detalles_nomina:
                    if detalle.empleado and detalle.proyecto and detalle.proyecto.cuenta:
                        try:
                            cuenta = detalle.proyecto.cuenta
                            monto_a_descontar = detalle.total_pago

                            if monto_a_descontar <= 0:
                                logger.warning(f"Monto a descontar para {detalle.empleado.nombre} es cero o negativo. No se realizará descuento.")
                                continue

                            if cuenta.saldo_actual < monto_a_descontar:
                                raise ValueError(
                                    f"Saldo insuficiente en la cuenta '{cuenta.cuenta}' "
                                    f"del proyecto '{detalle.proyecto.nombre}' para cubrir la nómina de '{detalle.empleado.nombre}'. "
                                    f"Saldo: {cuenta.saldo_actual}, Requerido: {monto_a_descontar}"
                                )

                            cuenta.saldo_actual -= monto_a_descontar
                            cuenta.save()
                            total_descontado_de_cuentas += monto_a_descontar
                            logger.debug(f"Descontado {monto_a_descontar} de la cuenta {cuenta.cuenta}. Nuevo saldo: {cuenta.saldo_actual}")

                        except ValueError as ve:
                            logger.error(f"Error de validación para NominaDetalle ID {detalle.id}: {ve}")
                            messages.error(request, f"Error al descontar el pago de {detalle.empleado.nombre}: {ve}")
                            raise
                        except Exception as e:
                            logger.error(f"Error inesperado al procesar NominaDetalle ID {detalle.id}: {e}", exc_info=True)
                            messages.error(request, f"Error interno al procesar el pago de {detalle.empleado.nombre}: {e}")
                            raise
                    else:
                        emp_nombre = detalle.empleado.nombre if detalle.empleado else 'N/A'
                        logger.warning(f"NominaDetalle ID {detalle.id} para '{emp_nombre}' sin proyecto o cuenta.")
                        messages.warning(request, f"No se pudo descontar el pago de {emp_nombre}; falta asignar proyecto o cuenta bancaria.")

                # Actualiza estatus y guarda
                nomina_historial.estatus = 'Procesada'
                nomina_historial.fecha_procesada = timezone.now()
                nomina_historial.save()
                logger.info(f"Nómina ID {nomina_historial.id} actualizada a estatus 'Procesada'. Total descontado: {total_descontado_de_cuentas}")

                messages.success(
                    request,
                    f"Nómina semana {nomina_historial.periodo_nomina.semana} "
                    f"({nomina_historial.periodo_nomina.periodo_inicio} al {nomina_historial.periodo_nomina.periodo_final}) "
                    f"cerrada exitosamente. Total descontado: ${total_descontado_de_cuentas:,.2f}."
                )
                return redirect('nom:nominas_cerradas_list')

        except NominaHistorial.DoesNotExist:
            logger.error(f"NominaHistorial con ID {nomina_historial_id} no encontrada.")
            messages.error(request, "La nómina que intenta cerrar no existe.")
            return redirect('nom:seleccionar_fecha')

        except ValueError as ve:
            logger.error(f"Fallo en transacción de cierre de nómina: {ve}")
            messages.error(request, f"Error de validación: {ve}")
            return redirect('nom:calcular_nomina')

        except Exception as e:
            logger.error(f"ERROR CRÍTICO al cerrar nómina ID {nomina_historial_id}: {e}", exc_info=True)
            messages.error(request, f"Ocurrió un error inesperado: {e}")
            return redirect('nom:calcular_nomina')

    logger.debug("--- FIN DE CERRAR_NOMINA (NO POST) ---")
    messages.warning(request, "Acceso inválido. Use el botón 'Cerrar Nómina'.")
    return redirect('nom:seleccionar_fecha')

@login_required(login_url='bases:login')
def nominas_cerradas_list(request):
    logger.debug("--- INICIO DE nominas_cerradas_list ---")
    
    # Filtramos las nóminas que tienen el estatus 'Cerrada'
    # Asumiendo que tu campo de estatus en NominaHistorial se llama 'estatus'
    # y el valor para 'Cerrada' es 'Cerrada'.
    nominas_cerradas = NominaHistorial.objects.filter(estatus='Procesada').order_by('-fecha_procesada')
    
    context = {
        'nominas_cerradas': nominas_cerradas,
        'titulo': 'Nóminas Cerradas', # Un título útil para la plantilla
    }
    
    logger.debug(f"Se encontraron {nominas_cerradas.count()} nóminas cerradas.")
    logger.debug("--- FIN DE nominas_cerradas_list ---")
    
    return render(request, 'nomina/nominas_cerradas_list.html', context)












#  def calcular_nomina_view(request):
#     form = FechaForm()
#     nomina = []
#     fecha_seleccionada = None
    


#     if request.method == "POST":
#         form = FechaForm(request.POST)
#         if form.is_valid():
            
#             fecha_seleccionada = form.cleaned_data['fecha']
#             nomina = calcular_nomina_semanal_todos(str(fecha_seleccionada))
            
#     return render(request, "nomina/nomina_semanal.html", {
#         "form": form,
#         "nomina": nomina,
#         "fecha": fecha_seleccionada
#     })
# 
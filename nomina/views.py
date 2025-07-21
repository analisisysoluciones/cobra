# nomina/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.views import generic
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
    EmpleadoForm, FaltaForm, FechaForm, PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
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



def guardar_periodo_sesion(request):
    if request.method == 'POST':
        periodo_id = request.POST.get('periodo_id')
        if not periodo_id:
            messages.error(request, "Debe seleccionar un período.")
            return redirect('nom:seleccionar_fecha')

        periodo = get_object_or_404(PeriodosNomina, pk=periodo_id)

        request.session['periodo_id'] = periodo.id
        request.session['periodo_semana'] = periodo.semana
        request.session['periodo_inicio'] = str(periodo.periodo_inicio)
        request.session['periodo_final'] = str(periodo.periodo_final)

        return redirect('nom:procesar_nomina_form')  # vista donde está el HTML procesar_nomina


def calcular_nomina_semanal_todos(fecha_inicio_semana):
    # Convertir la fecha de inicio de la semana a objeto date si es una cadena
    if isinstance(fecha_inicio_semana, str):
        try:
            fecha_inicio_semana = datetime.strptime(fecha_inicio_semana, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Formato de fecha incorrecto. Debe ser 'YYYY-MM-DD'.")
            return [] # Retorna una lista vacía si el formato es incorrecto

    # Calcular la fecha de fin de la semana (6 días después de la fecha de inicio, cubriendo 7 días en total)
    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    
    # Obtener todos los empleados activos
    empleados = Empleado.objects.filter(estado=True)
    
    nomina_lista = []
    DIAS_LABORALES_SEMANA = Decimal(6) # Definimos la constante para los días laborales esperados

    for empleado in empleados:
        print(f"Procesando empleado: {empleado.nombre}")
        
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
        # Si la política es que se pierde *todo* el 7mo día si hay *cualquier* falta:
        # descuento_septimo_dia = sueldo_diario if faltas > 0 else Decimal(0)
        # Si la política es un descuento proporcional (como tenías):
        descuento_septimo_dia = (faltas / DIAS_LABORALES_SEMANA) * sueldo_diario if faltas > 0 else Decimal(0)
        
        print(f"Descuento séptimo día para {empleado.nombre}: {descuento_septimo_dia}")

        # Percepciones: Sueldo semanal (por días trabajados) + Séptimo Día + Compensación
        percepciones = sueldo_semanal + septimo_dia + compensacion
        
        # Deducciones: Importe de las faltas + Descuento del Séptimo Día
        deducciones = importe_faltas + descuento_septimo_dia
        
        # Total a pagar
        total_pago = percepciones - deducciones

        nomina_lista.append({
            'empleado': empleado.nombre,
            'ingreso': empleado.ingreso, # Asumo que 'ingreso' es un campo en tu modelo Empleado
            'sueldo_diario': float(sueldo_diario),
            'dias_trabajados': int(dias_trabajados_para_sueldo), # Días pagados por sueldo base
            'faltas': faltas, # Días de falta contados
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

    return {
        'nomina': nomina_lista,
        'fecha_inicio': fecha_inicio_semana,
        'fecha_fin': fecha_fin_semana,
        'total_percepciones_general': total_percepciones_general,
        'total_deducciones_general': total_deducciones_general,
        'total_neto_general': total_neto_general,
    }

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

# ✅ Vista para seleccionar la fecha
@login_required(login_url='bases:login')
def seleccionar_fecha(request):
    if request.method == 'POST':
        form = FechaForm(request.POST)
        if form.is_valid():
            fecha_seleccionada = form.cleaned_data['fecha'].strftime('%Y-%m-%d')
            return redirect(reverse('nom:calcular_nomina') + f'?fecha={fecha_seleccionada}')
    else:
        form = FechaForm()
    return render(request, 'nomina/procesar_nomina.html', {'form': form})


# ✅ Vista para mostrar el cálculo de nómina
@login_required(login_url='bases:login')
def calcular_nomina_view(request):
    # Inicializamos el formulario y las variables para la plantilla de selección
    form = SeleccionarPeriodoForm()
    
    # Variables para la plantilla de resultados, inicialmente None o vacías
    nomina_calculada = [] 
    fecha_inicio_obj = None
    fecha_fin_obj = None
    nomina_existente = False
    periodo_obj_id = None
    cuentas = Cuenta.objects.all() # Asegúrate de que 'cuentas' se cargue para el select de guardar

    # Inicializamos el resto del contexto para la tabla de totales
    context_totales = {
        'total_percepciones': Decimal(0),
        'total_deducciones': Decimal(0),
        'total_neto_general': Decimal(0),
    }

    if request.method == 'POST':
        form = SeleccionarPeriodoForm(request.POST)
        
        if form.is_valid():
            periodo_obj = form.cleaned_data['periodo']
            periodo_obj_id = periodo_obj.id # Capturamos el ID del período
            fecha_inicio_obj = periodo_obj.periodo_inicio
            fecha_fin_obj = periodo_obj.periodo_final
            
            try:
                # Llama a tu función de cálculo de nómina
                nomina_resultados_brutos = calcular_nomina_semanal_todos(fecha_inicio_obj)
                
                nomina_calculada = nomina_resultados_brutos.get('nomina', [])
                context_totales['total_percepciones'] = nomina_resultados_brutos.get('total_percepciones', Decimal(0))
                context_totales['total_deducciones'] = nomina_resultados_brutos.get('total_deducciones', Decimal(0))
                context_totales['total_neto_general'] = nomina_resultados_brutos.get('total_neto_general', Decimal(0))

                # Verificamos si ya existe una nómina procesada para este período
                nomina_existente = NominaHistorial.objects.filter(
                    periodo_inicio=fecha_inicio_obj,
                    periodo_fin=fecha_fin_obj,
                    estatus='Procesada'
                ).exists()

                messages.success(request, f"Nómina calculada para el período ID: {periodo_obj.id} | Semana: {periodo_obj.semana} | Del {fecha_inicio_obj.strftime('%d/%m/%Y')} al {fecha_fin_obj.strftime('%d/%m/%Y')}.")

                # --- ¡CAMBIO CLAVE AQUÍ! ---
                # Si todo es exitoso, renderizamos la plantilla que muestra la tabla de nómina
                context_resultados = {
                    'nomina': nomina_calculada,
                    'fecha_inicio': fecha_inicio_obj, # Pasa los objetos datetime
                    'fecha_fin': fecha_fin_obj,       # Pasa los objetos datetime
                    'nomina_existente': nomina_existente,
                    'periodo_id': periodo_obj_id,
                    'periodo': periodo_obj, 
                    'cuentas': cuentas, # Asegúrate de pasar las cuentas para el select de guardar
                    **context_totales
                }
                return render(request, 'nomina/nomina_semanal.html', context_resultados) # <-- Renderiza la plantilla de la tabla
                
            except Exception as e:
                messages.error(request, f"Error al calcular la nómina: {e}")
                # Si hay un error, volvemos a renderizar el formulario de selección
                # con el formulario y sus errores.
                context_form_error = {
                    'form': form,
                    'cuentas': cuentas # Asegúrate de pasar las cuentas si el formulario de guardar está en esta página
                }
                return render(request, 'nomina/seleccionar_fecha.html', context_form_error)
        else:
            # Si el formulario no es válido (ej. el usuario no seleccionó nada)
            messages.warning(request, "Debe seleccionar un período de nómina válido.")
            # Renderizamos la plantilla de selección con el formulario y sus errores
            context_form_invalid = {
                'form': form,
                'cuentas': cuentas # Asegúrate de pasar las cuentas
            }
            return render(request, 'nomina/seleccionar_fecha.html', context_form_invalid)

    # Si la solicitud es GET (primera carga de la página de selección)
    # Renderizamos la plantilla de selección con el formulario vacío
    context_initial_get = {
        'form': form,
        'cuentas': cuentas # Asegúrate de pasar las cuentas
    }
    return render(request, 'nomina/seleccionar_fecha.html', context_initial_get)


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

@login_required(login_url='bases:login')
def generar_nomina_pdf(request):
    fecha_str = request.GET.get('fecha')
    if not fecha_str:
        messages.error(request, "Fecha no proporcionada para generar el PDF.")
        return redirect('nom:seleccionar_fecha')

    try:
        fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha incorrecto.")
        return redirect('nom:seleccionar_fecha')

    nomina_data = calcular_nomina_semanal_todos(fecha_str)

    if not nomina_data:
        messages.error(request, "No hay datos para generar el PDF.")
        return redirect('nom:seleccionar_fecha')

    total_percepciones = sum(Decimal(str(item['total_percepciones'])) for item in nomina_data)
    total_deducciones = sum(Decimal(str(item['total_deducciones'])) for item in nomina_data)
    total_neto_general = sum(Decimal(str(item['total_pago'])) for item in nomina_data)

    context = {
        'fecha_inicio': fecha_inicio,
        'nomina': nomina_data,
        'total_percepciones': total_percepciones,
        'total_deducciones': total_deducciones,
        'total_neto_general': total_neto_general,
    }
    
    template_path = 'nomina/nomina_pdf_template.html'
    html = render_to_string(template_path, context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="nomina_semanal_{fecha_str}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        messages.error(request, "Error al generar el PDF.")
        return redirect('nom:seleccionar_fecha')
    return response

@login_required(login_url='bases:login')
def generar_nomina_individual_pdf(request):
    fecha_inicio_str = request.GET.get('fecha_inicio')
    if not fecha_inicio_str:
        messages.error(request, "Fecha no proporcionada para generar recibos.")
        return redirect('nom:seleccionar_fecha')

    try:
        fecha_inicio_periodo = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha incorrecto.")
        return redirect('nom:seleccionar_fecha')

    nomina_historial = get_object_or_404(NominaHistorial, periodo_inicio=fecha_inicio_periodo)
    detalles_nomina = NominaDetalle.objects.filter(nomina_historica=nomina_historial).order_by('empleado__nombre')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="recibos_nomina_{fecha_inicio_str}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    for detalle in detalles_nomina:
        elements.append(Table([[f"Recibo de Nómina - {detalle.empleado.nombre}"]]))
        elements.append(Table([[f"Periodo: {nomina_historial.periodo_inicio} - {nomina_historial.periodo_fin}"]]))
        elements.append(Table([[f"Sueldo Diario: ${detalle.sueldo_diario}"]]))
        elements.append(Table([[f"Días Trabajados: {detalle.dias_trabajados}"]]))
        elements.append(Table([[f"Total: ${detalle.total_pago}"]]))
        elements.append(Table([[""], ["---"], [""]])) # Separador

    doc.build(elements)
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





@login_required(login_url='bases:login')
def seleccionar_periodo_nomina(request):
    if request.method == 'POST':
        form = SeleccionarPeriodoForm(request.POST)
        if form.is_valid():
            periodo = form.cleaned_data['periodo']

            # Guardar los datos en la sesión
            request.session['periodo_id'] = periodo.id
            request.session['periodo_semana'] = periodo.semana
            request.session['periodo_inicio'] = str(periodo.periodo_inicio)
            request.session['periodo_final'] = str(periodo.periodo_final)

            return redirect('nom:calcular_nomina')  # Redirecciona a la vista que muestra datos
    else:
        form = SeleccionarPeriodoForm()

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



















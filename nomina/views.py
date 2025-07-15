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
    Cuenta, Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo)
from inv.models import Material
from adm.models import MovimientoCuenta
from .forms import (
    EmpleadoForm, FaltaForm, FechaForm, PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm
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
    return render(request, 'nomina/seleccionar_fecha.html', {'form': form})


# ✅ Vista para mostrar el cálculo de nómina
@login_required(login_url='bases:login')
def calcular_nomina_view(request):
    fecha_str = request.GET.get('fecha')
    
    print("[DEBUG] calcular_nomina_view ejecutada")
    print("Fecha GET:", fecha_str) # Cambiado a fecha_str directamente

    context = {
        'nomina': [],
        'fecha_inicio': None, # Usaremos fecha_inicio y fecha_fin para un rango claro
        'fecha_fin': None,
        'total_percepciones': Decimal(0),
        'total_deducciones': Decimal(0),
        'total_neto_general': Decimal(0),
        'nomina_existente': False,
    }

    if fecha_str:
        try:
            # La función calcular_nomina_semanal_todos ahora devuelve un diccionario con todos los datos,
            # incluyendo los totales y las fechas de inicio y fin ya formateadas.
            nomina_result = calcular_nomina_semanal_todos(fecha_str)
            
            # Actualizamos el contexto con todos los datos que nos devuelve la función de cálculo.
            context.update(nomina_result)
            
            # Verificar si la nómina ya existe para este periodo.
            # Usamos context.get() para evitar errores si las fechas no se establecieron por alguna razón.
            if context.get('fecha_inicio') and context.get('fecha_fin'):
                context['nomina_existente'] = NominaHistorial.objects.filter(
                    periodo_inicio=context['fecha_inicio'],
                    # Si NominaHistorial usa fecha_fin, la incluyes. 
                    # Si solo guarda periodo_inicio, puedes omitir la siguiente línea.
                    # periodo_fin=context['fecha_fin'] 
                ).exists()
            else:
                context['nomina_existente'] = False # No hay fechas válidas para verificar existencia

            messages.success(request, f"Nómina calculada para la semana que inicia el {context['fecha_inicio'].strftime('%d/%m/%Y')}.")

        except ValueError:
            messages.error(request, "Formato de fecha incorrecto. Debe ser 'YYYY-MM-DD'.")
            return redirect('nom:seleccionar_fecha')
        except Exception as e:
            # Captura cualquier otra excepción que pueda ocurrir en el cálculo
            print(f"[ERROR en calcular_nomina_view] {e}")
            messages.error(request, f"Ocurrió un error al calcular la nómina: {e}")
            return redirect('nom:seleccionar_fecha')
    else:
        messages.warning(request, "Por favor, seleccione una fecha para calcular la nómina.")
        return redirect('nom:seleccionar_fecha')

    # Renderiza la plantilla con el contexto ya poblado por la función de cálculo
    return render(request, 'nomina/nomina_semanal.html', context)


@login_required(login_url='bases:login')
def procesar_nomina(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha_inicio_nomina') 
        cuenta_id = request.POST.get('cuenta') # Asumo que también pasarás la cuenta desde el formulario

        if not fecha_str:
            messages.error(request, "No se proporcionó la fecha de inicio de la nómina para procesar.")
            return redirect('nom:seleccionar_fecha')

        if not cuenta_id:
            messages.error(request, "No se proporcionó la cuenta para la nómina.")
            return redirect('nom:seleccionar_fecha')

        try:
            fecha_inicio = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            fecha_fin = fecha_inicio + timedelta(days=6)
            
            # Recupera el objeto Cuenta
            cuenta_obj = Cuenta.objects.get(id=cuenta_id)

            nomina_result = calcular_nomina_semanal_todos(fecha_str)
            nomina_data_list = nomina_result.get('nomina', []) 
            
            if not nomina_data_list:
                messages.warning(request, "No hay datos de nómina para procesar en el período seleccionado.")
                return redirect('nom:calcular_nomina') 

            # 2. Verificar si la nómina para este periodo ya existe en el historial
            if NominaHistorial.objects.filter(periodo_inicio=fecha_inicio, periodo_fin=fecha_fin, estatus='Procesada').exists():
                messages.info(request, f"La nómina para la semana del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')} ya fue procesada anteriormente.")
                return redirect('nom:calcular_nomina') 

            # 3. Guardar el registro de la nómina en NominaHistorial
            # AHORA SÓLO PASAMOS LOS CAMPOS QUE REALMENTE EXISTEN EN TU MODELO NominaHistorial
            nomina_historial = NominaHistorial.objects.create(
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                total_pago=nomina_result.get('total_neto_general', Decimal(0)), # total_neto_general de la función de cálculo
                cuenta=cuenta_obj, # Asigna el objeto Cuenta
                estatus='Procesada', # Se procesa y se marca como Procesada
                # fecha_procesada se asigna automáticamente en el método save del modelo
            )

            # 4. Guardar los detalles individuales de la nómina
            for item_data in nomina_data_list: 
                try:
                    empleado_obj = Empleado.objects.get(nombre=item_data['empleado'])
                except Empleado.DoesNotExist:
                    print(f"Advertencia: Empleado {item_data['empleado']} no encontrado en la base de datos. Saltando este registro.")
                    continue

                # Noté que NominaDetalle es el nombre de tu modelo, no DetalleNomina.
                # Además, el campo de FK es 'nomina_historica', no 'nomina_historial'.
                NominaDetalle.objects.create(
                    nomina_historica=nomina_historial, # Corregido a nomina_historica
                    empleado=empleado_obj,
                    sueldo_diario=item_data.get('sueldo_diario', Decimal(0)),
                    dias_trabajados=item_data.get('dias_trabajados', 0),
                    # Los campos de detalle deben coincidir con NominaDetalle
                    total_pago=item_data.get('total_pago', Decimal(0)), # Este es el total pago individual
                    proyecto=item_data.get('proyecto', None), # Asumo que 'proyecto' viene en item_data o es None inicialmente
                )
            
            messages.success(request, "Nómina procesada y guardada exitosamente.")
            
            # Redirige a la vista de asignación de proyectos con el ID de la nómina recién creada
            return redirect('nom:asignar_proyectos_nomina', nomina_id=nomina_historial.id)

        except Cuenta.DoesNotExist:
            messages.error(request, "La cuenta seleccionada no existe.")
            return redirect('nom:seleccionar_fecha')
        except ValueError as e:
            messages.error(request, f"Error en el formato de fecha: {e}. Asegúrese de que sea 'YYYY-M-D'.")
            return redirect('nom:seleccionar_fecha')
        except Exception as e:
            print(f"[ERROR procesar_nomina] {e}")
            messages.error(request, f"Ocurrió un error inesperado al procesar la nómina: {e}. Por favor, revise los logs del servidor.")
            return redirect('nom:seleccionar_fecha')
    
    messages.warning(request, "Acceso inválido. Por favor, use el formulario para procesar la nómina.")
    return redirect('nom:seleccionar_fecha')

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



























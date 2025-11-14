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
from nomina.models import (
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, TipoDestajo, TarifaDiariaObra, TarifaDestajoObra,
    RegistroDestajo
    )
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from nomina.forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaEmpleadoProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, 
    TipoDestajoForm
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
from django.db.models import Sum, Max, Q, Count, F, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from decimal import Decimal
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader





DATE_FMT = '%Y-%m-%d'  # lo que envía <input type="date">

def asignaciones_masivas(request):
    empleados = Empleado.objects.all().order_by('nombre')
    proyectos = Proyecto.objects.all().order_by('nombre')

    if request.method == 'POST':
        empleados_ids = request.POST.getlist('empleados')
        proyecto_id = (request.POST.get('proyecto') or '').strip()

        # 👇 OJO: deben llamarse exactamente así en el HTML
        fecha_inicio_str = (request.POST.get('fecha_inicio') or '').strip()
        fecha_fin_str    = (request.POST.get('fecha_fin') or '').strip()

        horas_str = (request.POST.get('horas_trabajadas') or '').strip()

        # Depuración útil (puedes comentar esto luego)
        #messages.info(
        #    request,
        #    f"DEBUG → recibido: proyecto={proyecto_id}, fecha_inicio='{fecha_inicio_str}', fecha_fin='{fecha_fin_str}', horas='{horas_str}', empleados={empleados_ids}"
        #)

        # === Validar requeridos ===
        if not empleados_ids or not proyecto_id or not fecha_inicio_str or not fecha_fin_str:
            messages.error(request, "Selecciona al menos un empleado, un proyecto y el rango de fechas.")
            return render(request, 'nomina/asignacion_masiva.html', {'empleados': empleados, 'proyectos': proyectos})

        # === Parseo de fechas (formato de <input type='date'>: YYYY-MM-DD) ===
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, DATE_FMT).date()
            fecha_fin    = datetime.strptime(fecha_fin_str,    DATE_FMT).date()
        except ValueError:
            messages.error(request, "Formato de fecha inválido. Usa el selector (YYYY-MM-DD).")
            return render(request, 'nomina/asignacion_masiva.html', {'empleados': empleados, 'proyectos': proyectos})

        # === Comparación correcta (tipo date) ===
        if fecha_fin < fecha_inicio:
            messages.error(
                request,
                f"La fecha final no puede ser anterior a la inicial. Recibido: Desde {fecha_inicio} Hasta {fecha_fin}"
            )
            return render(request, 'nomina/asignacion_masiva.html', {'empleados': empleados, 'proyectos': proyectos})

        # === Validar horas ===
        try:
            horas = float(horas_str) if horas_str != '' else 0.0
            if not (0 <= horas <= 12):
                raise ValueError("rango inválido")
        except ValueError:
            messages.error(request, "Las horas trabajadas deben ser un número entre 0 y 12.")
            return render(request, 'nomina/asignacion_masiva.html', {'empleados': empleados, 'proyectos': proyectos})

        # === Crear asignaciones por cada día del rango ===
        errores = []
        total_registros = 0
        dias = (fecha_fin - fecha_inicio).days + 1

        with transaction.atomic():
            for emp_id in empleados_ids:
                empleado = Empleado.objects.get(id=emp_id)
                for d in range(dias):
                    fecha_actual = fecha_inicio + timedelta(days=d)

                    # Duplicado exacto
                    if AsignacionDiaria.objects.filter(
                        empleado_id=emp_id, fecha=fecha_actual, proyecto_id=proyecto_id
                    ).exists():
                        errores.append(
                            f"Ya existe asignación para {empleado} el {fecha_actual.strftime('%d/%m/%Y')} en ese proyecto."
                        )
                        continue

                    # Límite 12h
                    total_horas = AsignacionDiaria.objects.filter(
                        empleado_id=emp_id, fecha=fecha_actual
                    ).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
                    if total_horas + horas > 12:
                        errores.append(
                            f"{empleado} excedería 12h el {fecha_actual.strftime('%d/%m/%Y')} (actual: {total_horas}, nuevas: {horas})."
                        )
                        continue

                    AsignacionDiaria.objects.create(
                        empleado_id=emp_id,
                        proyecto_id=proyecto_id,
                        fecha=fecha_actual,
                        horas_trabajadas=horas
                    )
                    total_registros += 1

        for e in errores:
            messages.error(request, e)

        if total_registros:
            messages.success(
                request,
                f"Se asignó el proyecto a {len(empleados_ids)} empleado(s) del {fecha_inicio} al {fecha_fin}. "
                f"Registros creados: {total_registros}."
            )
        else:
            messages.warning(request, "No se generaron nuevas asignaciones (duplicados/validaciones).")

        return redirect('nom:asignacion_list')

    return render(request, 'nomina/asignacion_masiva.html', {'empleados': empleados, 'proyectos': proyectos})



@login_required
def asignar_semana_todos(request):
    periodo_id = request.session.get('periodo_id')
    if not periodo_id:
        messages.error(request, "Seleccione un período primero.")
        return redirect('nom:seleccionar_fecha')
    
    periodo = get_object_or_404(PeriodosNomina, id=periodo_id)
    dias_semana = [periodo.periodo_inicio + timedelta(days=i) for i in range(6)]  # Lunes-Sábado
    empleados = Empleado.objects.filter(estado=True)
    proyectos = Proyecto.objects.all()
    
    # Pre-cargar asignaciones existentes
    asignaciones_qs = AsignacionDiaria.objects.filter(empleado__in=empleados, fecha__in=dias_semana)
    formset = AsignacionDiariaFormSet(queryset=asignaciones_qs)
    
    if request.method == 'POST':
        formset = AsignacionDiariaFormSet(request.POST, queryset=asignaciones_qs)
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    instance = form.save(commit=False)
                    # Asigna empleado/fecha desde POST si nuevo
                    # Validación extra: Si falta añadida después, warning pero save
                    if Asistencia.objects.filter(empleado=instance.empleado, fecha=instance.fecha).exists():
                        messages.warning(request, f"Asignación para {instance.empleado} en {instance.fecha} tiene falta posterior. Revise.")
                    instance.save()
            messages.success(request, "Asignaciones guardadas.")
            return redirect('nom:calcular_nomina')
        else:
            messages.error(request, "Errores en asignaciones. Verifique faltas.")
    
    context = {
        'formset': formset,
        'periodo': periodo,
        'dias_semana': dias_semana,
        'empleados': empleados,
        'proyectos': proyectos,
    }
    return render(request, 'nomina/asignar_semanal.html', context)


class AsignacionListView(generic.ListView):
    model = AsignacionDiaria
    template_name = 'nomina/asignacion_list.html'
    context_object_name = 'asignaciones'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo_activo = NominaHistorial.objects.filter(estatus='ABIERTO').last()
        context['periodo'] = periodo_activo
        return context

class AsignacionCreateView(generic.CreateView):
    model = AsignacionDiaria
    form_class = AsignacionDiariaForm
    template_name = 'nomina/asignacion_form.html'
    success_url = reverse_lazy('nom:asignacion_list')

    

class AsignacionUpdateView(generic.UpdateView):
    model = AsignacionDiaria
    form_class = AsignacionDiariaForm
    template_name = 'nomina/asignacion_form.html'
    success_url = reverse_lazy('nom:asignacion_list')

    
class AsignacionDeleteView(generic.DeleteView):
    model = AsignacionDiaria
    template_name = 'nomina/asignacion_confirm_delete.html'
    success_url = reverse_lazy('nom:asignacion_list')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        print(obj.fecha, obj.empleado, obj.proyecto, obj.horas_trabajadas)  # Depuración
        return obj
    
def crear_asignacion_diaria(request):
    if request.method == 'POST':
        form = AsignacionDiariaForm(request.POST)
        if form.is_valid():
            asignacion = form.save()
           
            messages.success(request, "Asignación registrada correctamente.")
            return redirect('nom:seleccionar_fecha')  # O a una lista de asignaciones
        else:
            
            messages.error(request, "Error al registrar la asignación. Verifica los datos.")
    else:
        form = AsignacionDiariaForm()

    return render(request, 'nomina/crear_asignacion_diaria.html', {'form': form})



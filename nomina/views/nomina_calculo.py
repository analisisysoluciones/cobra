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
from django.core.cache import cache
from decimal import Decimal, ROUND_HALF_UP
from nomina.models import (    
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, TipoDestajo, TarifaDiariaObra, TarifaDestajoObra,
    RegistroDestajo, HorasExtras, CompensacionVariable, NominaEmpleado
    )
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from nomina.forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaEmpleadoProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, TipoDestajoForm
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
from datetime import datetime, timedelta, date
from decimal import Decimal
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader




def poblar_nomina_detalle_desde_asignaciones(nomina_historial, horas_jornada=8):
    """
    Llena o actualiza los registros de NominaEmpleado y NominaDetalle
    para el periodo de nomina_historial a partir de AsignacionDiaria.
    Agrupa por empleado y proyecto.
    """
    qs = (
        AsignacionDiaria.objects
        .filter(fecha__range=(nomina_historial.periodo_inicio, nomina_historial.periodo_fin))
        .values('empleado', 'proyecto')
        .annotate(
            dias=Count('id'),
            horas=Coalesce(
                Sum('horas_trabajadas'),
                Value(0.0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )

    total_general = Decimal('0.00')
    registros_creados = 0

    for row in qs:
        emp = Empleado.objects.get(pk=row['empleado'])
        proyecto_id = row['proyecto']
        dias = int(row['dias'] or 0)
        horas = Decimal(row['horas'] or 0)

        # Buscar o crear NominaEmpleado
        nomina_emp, _ = NominaEmpleado.objects.get_or_create(
            historial=nomina_historial,
            empleado=emp,
            defaults={
                "dias_trabajados": dias,
                "total_percepciones": 0,
                "total_deducciones": 0,
                "total_neto": 0,
                "proyecto_id": proyecto_id,
            }
        )

        # Calcular total base según horas o días
        if horas > 0:
            total = (emp.sueldo_diario / Decimal(horas_jornada)) * horas
        else:
            total = emp.sueldo_diario * dias

        # Crear o actualizar el detalle
        NominaDetalle.objects.update_or_create(
            nomina_empleado=nomina_emp,
            concepto="Sueldo base",
            tipo="PERCEPCION",
            defaults={
                "cantidad": dias,
                "monto_unitario": emp.sueldo_diario,
                "subtotal": total
            }
        )

        total_general += total
        registros_creados += 1

    # Actualiza total de la nómina principal
    nomina_historial.total_pago = total_general
    nomina_historial.save()

    print(f"✅ {registros_creados} detalles creados para la nómina #{nomina_historial.id} — Total ${total_general:,.2f}")
    return registros_creados

#==================================================================
#  Aquí va el original
#==================================================================
# def calcular_nomina_semanal_todos(fecha_inicio_semana):
#     # --- Convertir fecha si llega como cadena ---
#     if isinstance(fecha_inicio_semana, str):
#         try:
#             fecha_inicio_semana = datetime.strptime(fecha_inicio_semana, "%Y-%m-%d").date()
#         except ValueError:
#             return {
#                 'nomina': [],
#                 'fecha_inicio': None,
#                 'fecha_fin': None,
#                 'total_percepciones_general': 0,
#                 'total_deducciones_general': 0,
#                 'total_neto_general': 0,
#             }

#     # --- Calcular rango de la semana ---
#     fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
#     empleados = Empleado.objects.filter(estado=True)
#     nomina_lista = []
#     DIAS_LABORALES_SEMANA = Decimal(6)

#     for empleado in empleados:
#         # Inicializa variables
#         sueldo_diario = Decimal(empleado.sueldo_diario or 0)
#         compensacion = Decimal(empleado.compensacion or 0)
#         percepciones = Decimal('0.00')
#         deducciones = Decimal('0.00')
#         total_pago = Decimal('0.00')
#         septimo_dia = Decimal('0.00')
#         sueldo_semanal = Decimal('0.00')

#         # --- Calcular faltas ---
#         dias_faltados_registrados = Asistencia.objects.filter(
#             empleado=empleado,
#             fecha__range=[fecha_inicio_semana, fecha_fin_semana]
#         ).count()
#         faltas = min(dias_faltados_registrados, DIAS_LABORALES_SEMANA)

#         # --- Cálculo base ---
#         dias_trabajados = DIAS_LABORALES_SEMANA - faltas
#         sueldo_semanal = dias_trabajados * sueldo_diario
#         septimo_dia = sueldo_diario if faltas == 0 else Decimal(0)
#         importe_faltas = faltas * sueldo_diario
#         descuento_septimo_dia = (faltas / DIAS_LABORALES_SEMANA) * sueldo_diario if faltas > 0 else Decimal(0)

#         # --- Calcular horas extras ---
#         extras = HorasExtras.objects.filter(
#             empleado=empleado,
#             fecha__range=[fecha_inicio_semana, fecha_fin_semana]
#         ).aggregate(total=Sum('total_pago'))['total'] or Decimal('0.00')

#         # --- Calcular destajos del empleado durante la semana ---

#         periodo_obj = PeriodosNomina.objects.filter(periodo_inicio=fecha_inicio_semana).first()

#         destajos = RegistroDestajo.objects.filter(
#             empleado=empleado,
#             semana=periodo_obj
#         ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

#         # --- Detalle de destajos ---
#         destajos_qs = RegistroDestajo.objects.filter(
#             empleado=empleado,
#             semana=periodo_obj
#         ).select_related('obra', 'tipo')

#         destajos_lista = [
#             {
#                 'obra': d.obra.nombre if d.obra else '—',
#                 'tipo': d.tipo.descripcion if hasattr(d.tipo, "descripcion") else str(d.tipo),
#                 'cantidad': float(d.cantidad or 0),
#                 'factor': float(d.factor or 0),
#                 'tarifa': float(d.tarifa_aplicada or 0),
#                 'total': float(d.total or 0),
#                 'descripcion': d.descripcion or '',
#             }
#             for d in destajos_qs
#         ]


#         # --- Percepciones ---
#         # --- Percepciones ---
#         percepciones = sueldo_semanal + septimo_dia + compensacion + extras + destajos


#         # --- Deducciones ---
#         deducciones = importe_faltas + descuento_septimo_dia

#         # --- Total a pagar ---
#         total_pago = percepciones - deducciones

#         # --- Agregar al listado ---
#         nomina_lista.append({
#             'empleado_id': empleado.id,
#             'empleado': empleado.nombre,
#             'codigo': empleado.codigo,
#             'ingreso': empleado.ingreso,
#             'sueldo_diario': float(sueldo_diario),
#             'dias_trabajados': int(dias_trabajados),
#             'faltas': int(faltas),
#             'importe_faltas': float(importe_faltas),
#             'sueldo_semanal': float(sueldo_semanal),
#             'septimo_dia': float(septimo_dia),
#             'compensacion': float(compensacion),
#             'horas_extras': float(extras),
#             'descuento_septimo_dia': float(descuento_septimo_dia),
#             'percepciones': float(percepciones),
#             'deducciones': float(deducciones),
#             'total_pago': float(total_pago),
#             'destajos': float(destajos),
#             'destajos_detalle': destajos_lista,


#         })

#     # --- Totales generales ---
#     total_percepciones_general = sum(item['percepciones'] for item in nomina_lista)
#     total_deducciones_general = sum(item['deducciones'] for item in nomina_lista)
#     total_neto_general = sum(item['total_pago'] for item in nomina_lista)

#     return {
#         'nomina': nomina_lista,
#         'fecha_inicio': fecha_inicio_semana,
#         'fecha_fin': fecha_fin_semana,
#         'total_percepciones_general': total_percepciones_general,
#         'total_deducciones_general': total_deducciones_general,
#         'total_neto_general': total_neto_general,
#     }
#=============================================================================
# calcular nomina view
#=============================================================================




def calcular_nomina_semanal_todos(periodo_input):
    """
    Cálculo de nómina real:
    Solo considera empleados con asignación en el periodo.
    """

    from decimal import Decimal, ROUND_HALF_UP

    periodo = _resolve_periodo(periodo_input)
    if not periodo:
        raise ValueError("No se encontró un período de nómina válido para el parámetro recibido.")

    fecha_inicio = periodo.periodo_inicio
    fecha_fin = periodo.periodo_final

    # 🔹 Solo empleados con asignación durante el periodo
    empleados = (
        Empleado.objects.filter(asignaciondiaria__fecha__range=(fecha_inicio, fecha_fin))
        .distinct()
    )

    nomina = []

    for emp in empleados:
        asign_qs = AsignacionDiaria.objects.filter(
            empleado=emp,
            fecha__range=(fecha_inicio, fecha_fin)
        )

        dias_trabajados = min(asign_qs.values("fecha").distinct().count(), 6)
        dias_no_trabajados = 6 - dias_trabajados

        sueldo_diario = Decimal(emp.sueldo_diario or 0).quantize(Decimal("0.01"))
        compensacion_fija = Decimal(emp.compensacion or 0).quantize(Decimal("0.01"))

        if dias_trabajados > 0:
            septimo_dia = (
                (Decimal(dias_trabajados) * sueldo_diario / Decimal(6))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            septimo_dia = Decimal("0.00")

        sueldo_base = (sueldo_diario * Decimal(dias_trabajados)).quantize(Decimal("0.01"))

        horas_extras_qs = HorasExtras.objects.filter(empleado=emp, periodo_id=periodo.id)
        horas_extras_total = Decimal(
            sum(h.total_pago for h in horas_extras_qs)
        ).quantize(Decimal("0.01")) if horas_extras_qs.exists() else Decimal("0.00")

        compensaciones_qs = CompensacionVariable.objects.filter(empleado=emp, periodo_id=periodo.id)
        compensacion_variable_total = Decimal(
            sum(c.monto for c in compensaciones_qs)
        ).quantize(Decimal("0.01")) if compensaciones_qs.exists() else Decimal("0.00")

        destajos_total = Decimal("0.00")

        percepciones = (
            sueldo_base +
            septimo_dia +
            compensacion_fija +
            compensacion_variable_total +
            horas_extras_total +
            destajos_total
        ).quantize(Decimal("0.01"))

        total_deducciones = Decimal("0.00")
        total_neto = (percepciones - total_deducciones).quantize(Decimal("0.01"))

        # Obtener el proyecto al que asistió durante el periodo
        proyecto_qs = (
            asign_qs.values_list("proyecto__id", "proyecto__nombre")
            .distinct()
        )
        if proyecto_qs.exists():
            proyecto_id, proyecto_nombre = proyecto_qs.first()
        else:
            proyecto_id, proyecto_nombre = None, ""

        nomina.append({
            "empleado_id": emp.id,
            "empleado": emp.nombre,
            "proyecto_id": proyecto_id,
            "proyecto": proyecto_nombre,
            "sueldo_diario": sueldo_diario,
            "dias_trabajados": dias_trabajados,
            "faltas": dias_no_trabajados,
            "sueldo_semanal": sueldo_base,
            "septimo_dia": septimo_dia,
            "compensacion_fija": compensacion_fija,
            "compensacion_variable": compensacion_variable_total,
            "horas_extras": horas_extras_total,
            "destajos": destajos_total,
            "total_percepciones": percepciones,
            "total_deducciones": total_deducciones,
            "total_pago": total_neto,
        })

    return {
        "nomina": nomina,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }

#================================================================================
#   **** fin calcular nomina todos ****
#================================================================================





# --- Tu vista principal (modificada) ---
import json
from pathlib import Path


def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

@login_required(login_url='bases:login')
def calcular_nomina_view(request):
    periodo_id = request.session.get("periodo_id")
    if not periodo_id:
        messages.error(request, "No se ha seleccionado un período de nómina.")
        return redirect("nom:seleccionar_fecha")

    periodo = get_object_or_404(PeriodosNomina, id=periodo_id)

    try:
        resultados = calcular_nomina_semanal_todos(periodo)
        nomina_data = resultados.get("nomina", [])
    except Exception as e:
        messages.error(request, f"Error al calcular la nómina: {e}")
        return redirect("nom:seleccionar_fecha")

    if not nomina_data:
        messages.info(request, "No se encontraron registros de nómina en este período.")
        return redirect("nom:seleccionar_fecha")

    # Totales
    # --- Totales generales seguros ---
    total_percepciones_general = sum(
        (
            r.get("sueldo_semanal", 0)
            + r.get("septimo_dia", 0)
            + r.get("compensacion_fija", 0)
            + r.get("compensacion_variable", 0)
            + r.get("horas_extras", 0)
        )
        for r in nomina_data
    )

    total_deducciones_general = sum(
        (
            r.get("importe_faltas", 0)
            + r.get("descuento_septimo_dia", 0)
        )
        for r in nomina_data
        if "importe_faltas" in r
    )

    total_neto_general = total_percepciones_general - total_deducciones_general

    # 🔒 Guardar copia exacta del cálculo (sin alterar lo que ves en pantalla)
    base_dir = Path(__file__).resolve().parent.parent
    tmp_path = base_dir / "tmp_nomina_data.json"
    nomina_serializable = convert_decimals(nomina_data)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(nomina_serializable, f, ensure_ascii=False, indent=2)
    print(f"✅ Archivo temporal guardado: {tmp_path} ({len(nomina_data)} registros)")

    context = {
        "periodo": periodo,
        "nomina": nomina_data,
        "total_percepciones_general": total_percepciones_general,
        "total_deducciones_general": total_deducciones_general,
        "total_neto_general": total_neto_general,
    }
    return render(request, "nomina/nomina_semanal.html", context)
#================================================================================
#   **** fin calcular nomina view ****
#================================================================================

@login_required
def reiniciar_nomina(request):
    for key in ['periodo_id', 'periodo_semana', 'periodo_inicio', 'periodo_final']:
        if key in request.session:
            del request.session[key]
    messages.info(request, "🔄 Se ha reiniciado la sesión de nómina. Puedes seleccionar el período nuevamente.")
    return redirect('nom:seleccionar_fecha')


# --- imports arriba del archivo ---
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from nomina.models import AsignacionDiaria, Empleado, PeriodosNomina, HorasExtras
# -----------------------------------

def _resolve_periodo(periodo_input):
    """
    Acepta: PeriodosNomina | int (id) | datetime | date | str(YYYY-MM-DD)
    Devuelve: PeriodosNomina o None
    """
    if isinstance(periodo_input, PeriodosNomina):
        return periodo_input

    if isinstance(periodo_input, int):
        return PeriodosNomina.objects.filter(pk=periodo_input).first()

    if isinstance(periodo_input, datetime):
        return PeriodosNomina.objects.filter(periodo_inicio=periodo_input.date()).first()

    if isinstance(periodo_input, date):
        return PeriodosNomina.objects.filter(periodo_inicio=periodo_input).first()

    if isinstance(periodo_input, str):
        try:
            d = datetime.strptime(periodo_input, "%Y-%m-%d").date()
            return PeriodosNomina.objects.filter(periodo_inicio=d).first()
        except Exception:
            return None

    return None

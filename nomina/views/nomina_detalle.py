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
from datetime import datetime, timedelta
from decimal import Decimal
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader

from nomina.models import NominaHistorial, NominaEmpleado, NominaDetalle, RegistroDestajo
from django.db.models import Sum, Q

def nomina_detalle(request, pk):
    """
    Muestra el detalle (movimientos) de una nómina, incluyendo destajos y horas extras por empleado.
    Estructura: NominaHistorial → NominaEmpleado → NominaDetalle.
    """
    nomina = get_object_or_404(NominaHistorial, pk=pk)

    empleados_nomina = NominaEmpleado.objects.filter(historial=nomina)

    # 🔹 Anotamos el total de horas extras por empleado (sumando los subtotales del concepto 'Horas extras')
    detalles = (
        NominaDetalle.objects
        .filter(nomina_empleado__in=empleados_nomina)
        .select_related("nomina_empleado__empleado", "nomina_empleado__proyecto")
        .annotate(
            horas_extras=Sum(
                "subtotal",
                filter=Q(concepto__icontains="hora")  # detecta 'Horas extras'
            )
        )
        .order_by("nomina_empleado__empleado__codigo")
    )

    # --- Calcular sueldos base ---
    total_sueldo = sum(
        det.monto_unitario * det.cantidad for det in detalles if det.tipo == "PERCEPCION"
    )

    # --- Calcular destajos ---
    destajos_por_empleado = {}
    total_destajos = 0

    for empleado_nomina in empleados_nomina:
        emp = empleado_nomina.empleado

        destajos_empleado = (
            RegistroDestajo.objects.filter(
                empleado=emp,
                semana__periodo_inicio=nomina.periodo_inicio,
                semana__periodo_final=nomina.periodo_fin,
            ).aggregate(total=Sum("total"))["total"]
            or 0
        )

        destajos_por_empleado[emp.id] = destajos_empleado
        total_destajos += destajos_empleado

    total_pago = sum(det.subtotal for det in detalles if det.tipo == "PERCEPCION")
    total_general = total_pago + total_destajos

    context = {
        "titulo": f"Detalle de Nómina #{nomina.id}",
        "nomina": nomina,
        "detalles": detalles,
        "destajos_por_empleado": destajos_por_empleado,
        "total_sueldo": total_sueldo,
        "total_pago": total_pago,
        "total_destajos": total_destajos,
        "total_general": total_general,
    }

    if not detalles.exists():
        messages.warning(request, "No hay registros asociados a esta nómina.")

    print(f"📊 Nómina {nomina.id}: {detalles.count()} detalles, total general ${total_general:.2f}")

    return render(request, "nomina/nomina_detalle.html", context)

@login_required(login_url='bases:login')
def listar_detalles_nomina_procesada(request, nomina_historial_id):
    """
    Vista para listar los detalles de una nómina histórica específica.
    """
    nomina_historial = get_object_or_404(NominaHistorial, id=nomina_historial_id)
    detalles_nomina = NominaDetalle.objects.filter(nomina_empleado=nomina_historial).order_by('empleado__nombre')

    context = {
        'nomina_historial': nomina_historial,
        'detalles_nomina': detalles_nomina,
    }
    return render(request, 'nomina/nomina_detalle.html', context)


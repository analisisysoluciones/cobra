from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, Count, Value, DecimalField
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.functions import Coalesce
from adm.models import Proyecto
from nomina.models import (
    Empleado, AsignacionDiaria,
    HorasExtras, CompensacionVariable,
    NominaEmpleado, NominaDetalle,
    MovimientoCuentaProyecto
)

# ============================================================
#  BASE DESDE ASIGNACIONES (SUELDO BASE)
# ============================================================
def poblar_base_desde_asignaciones(nomina_historial, horas_jornada=8):
    """
    Genera registros base de nómina desde AsignacionDiaria,
    agrupando por empleado y proyecto.
    Calcula sueldo_diario * días trabajados.
    También registra MovimientoCuentaProyecto por proyecto.
    """

    qs = (
        AsignacionDiaria.objects
        .filter(fecha__range=(nomina_historial.periodo_inicio, nomina_historial.periodo_fin))
        .values('empleado', 'proyecto')
        .annotate(
            dias=Count('id'),
            horas=Coalesce(
                Sum('horas_trabajadas'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )

    for row in qs:
        emp = Empleado.objects.get(pk=row['empleado'])
        proyecto_id = row['proyecto']
        dias = Decimal(row['dias'] or 0)
        horas = Decimal(row['horas'] or 0)

        proyecto = Proyecto.objects.filter(pk=proyecto_id).first()
        cuenta = proyecto.cuenta if proyecto and hasattr(proyecto, "cuenta") else None

        # Buscar o crear encabezado NominaEmpleado
        nom_emp, _ = NominaEmpleado.objects.get_or_create(
            historial=nomina_historial,
            empleado=emp,
            proyecto=proyecto,
            defaults={
                'total_percepciones': Decimal('0.00'),
                'total_deducciones': Decimal('0.00'),
                'total_neto': Decimal('0.00')
            }
        )

        # Cálculo del sueldo base
        total = (emp.sueldo_diario * dias).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Crear detalle
        NominaDetalle.objects.create(
            nomina_empleado=nom_emp,
            concepto=f"Sueldo base ({dias} días, {horas} hrs)",
            tipo='PERCEPCION',
            cantidad=dias,
            monto_unitario=emp.sueldo_diario,
            subtotal=total
        )

        # Crear movimiento contable por proyecto
        if proyecto and cuenta:
            MovimientoCuentaProyecto.objects.create(
                proyecto=proyecto,
                empleado=emp,
                periodo=nomina_historial,
                importe=total
            )


# ============================================================
#  HORAS EXTRAS
# ============================================================
def poblar_horas_extras(nomina_historial):
    """
    Agrega movimientos de horas extras a la nómina.
    También registra MovimientoCuentaProyecto.
    """

    extras = (
        HorasExtras.objects
        .filter(fecha__range=(nomina_historial.periodo_inicio, nomina_historial.periodo_fin))
        .select_related('empleado', 'proyecto')
    )

    for hx in extras:
        proyecto = hx.proyecto
        cuenta = proyecto.cuenta if proyecto and hasattr(proyecto, "cuenta") else None

        nom_emp, _ = NominaEmpleado.objects.get_or_create(
            historial=nomina_historial,
            empleado=hx.empleado,
            proyecto=proyecto,
            defaults={
                'total_percepciones': Decimal('0.00'),
                'total_deducciones': Decimal('0.00'),
                'total_neto': Decimal('0.00')
            }
        )

        subtotal = (hx.horas * hx.pago_por_hora).quantize(Decimal('0.01'))

        NominaDetalle.objects.create(
            nomina_empleado=nom_emp,
            concepto=f"Horas extras ({hx.horas} hrs)",
            tipo='PERCEPCION',
            cantidad=hx.horas,
            monto_unitario=hx.pago_por_hora,
            subtotal=subtotal
        )

        if proyecto and cuenta:
            MovimientoCuentaProyecto.objects.create(
                proyecto=proyecto,
                empleado=hx.empleado,
                periodo=nomina_historial,
                importe=subtotal
            )


# ============================================================
#  COMPENSACIÓN VARIABLE
# ============================================================
def poblar_compensacion_variable(nomina_historial):
    """
    Inserta las compensaciones variables (bonos, incentivos)
    y registra MovimientoCuentaProyecto.
    """

    comps = (
        CompensacionVariable.objects
        .filter(fecha__range=(nomina_historial.periodo_inicio, nomina_historial.periodo_fin))
        .select_related('empleado', 'proyecto')
    )

    for cv in comps:
        proyecto = cv.proyecto
        cuenta = proyecto.cuenta if proyecto and hasattr(proyecto, "cuenta") else None

        nom_emp, _ = NominaEmpleado.objects.get_or_create(
            historial=nomina_historial,
            empleado=cv.empleado,
            proyecto=proyecto,
            defaults={
                'total_percepciones': Decimal('0.00'),
                'total_deducciones': Decimal('0.00'),
                'total_neto': Decimal('0.00')
            }
        )

        monto = Decimal(cv.monto or 0).quantize(Decimal('0.01'))

        NominaDetalle.objects.create(
            nomina_empleado=nom_emp,
            concepto=f"Compensación variable ({cv.concepto})",
            tipo='PERCEPCION',
            cantidad=Decimal('1.00'),
            monto_unitario=monto,
            subtotal=monto
        )

        if proyecto and cuenta:
            MovimientoCuentaProyecto.objects.create(
                proyecto=proyecto,
                empleado=cv.empleado,
                periodo=nomina_historial,
                importe=monto
            )


# ============================================================
#  RE-CÁLCULO DE TOTALES
# ============================================================
def recalcular_totales_nomina(nomina_historial):
    """
    Recalcula los totales por empleado y el total general.
    """

    empleados = NominaEmpleado.objects.filter(historial=nomina_historial)
    total_nomina = Decimal('0.00')

    for ne in empleados:
        percepciones = (
            NominaDetalle.objects.filter(nomina_empleado=ne, tipo='PERCEPCION')
            .aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        )
        deducciones = (
            NominaDetalle.objects.filter(nomina_empleado=ne, tipo='DEDUCCION')
            .aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        )

        percepciones = Decimal(percepciones).quantize(Decimal('0.01'))
        deducciones = Decimal(deducciones).quantize(Decimal('0.01'))
        total_neto = (percepciones - deducciones).quantize(Decimal('0.01'))

        ne.total_percepciones = percepciones
        ne.total_deducciones = deducciones
        ne.total_neto = total_neto
        ne.save()

        total_nomina += total_neto

    nomina_historial.total_pago = total_nomina.quantize(Decimal('0.01'))
    nomina_historial.save()



def comparativo_proyecto(proyecto_id):

    ejecucion = EjecucionActividad.objects.filter(proyecto_id=proyecto_id)

    resultado = {}

    for e in ejecucion:
        key = e.actividad.nombre

        if key not in resultado:
            resultado[key] = {
                "real": 0,
                "estimado": 0
            }

        resultado[key]["real"] += float(e.costo_real)

    presupuestos = PresupuestoActividad.objects.filter(proyecto_id=proyecto_id)

    for p in presupuestos:
        key = p.actividad.nombre

        if key not in resultado:
            resultado[key] = {
                "real": 0,
                "estimado": 0
            }

        resultado[key]["estimado"] += float(p.costo_estimado)

    return resultado
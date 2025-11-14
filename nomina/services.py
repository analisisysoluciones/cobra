# nomina/services.py
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Q

from .models import (
    PeriodosNomina, AsistenciaDia, TarifaDiariaObra,
    RegistroDestajo, GastoObra
)

EXTRA_MULTIPLICADOR = Decimal("1.0")  # si luego quieres pagar HE distinto, ajusta aquí

def obtener_tarifa_dia(obra, empleado):
    # prioridad: tarifa específica por empleado; si no hay, tarifa general para la obra
    q = TarifaDiariaObra.objects.filter(obra=obra, empleado=empleado)
    if q.exists():
        return q.first().monto_dia
    q = TarifaDiariaObra.objects.filter(obra=obra, empleado__isnull=True)
    return q.first().monto_dia if q.exists() else Decimal("0")

@transaction.atomic
def recalcular_semana(semana_id: int):
    semana = PeriodosNomina.objects.select_for_update().get(id=semana_id)

    # Sueldos por día trabajado (+ horas extra si aplica)
    total_sueldos = Decimal("0")
    # agrupamos por empleado+obra
    asistencias = (AsistenciaDia.objects
                   .filter(semana=semana)
                   .select_related("empleado", "obra"))
    # suma por empleado
    cache_tarifas = {}  # (obra_id, emp_id) -> tarifa
    por_empleado = {}

    for a in asistencias:
        key = (a.obra_id, a.empleado_id)
        if key not in cache_tarifas:
            cache_tarifas[key] = obtener_tarifa_dia(a.obra, a.empleado)
        tarifa_dia = cache_tarifas[key]
        monto_dia = Decimal(a.laboro) * tarifa_dia
        monto_he = Decimal(a.horas_extra) * (tarifa_dia / Decimal("8")) * EXTRA_MULTIPLICADOR
        total = monto_dia + monto_he
        total_sueldos += total
        por_empleado.setdefault(a.empleado_id, Decimal("0"))
        por_empleado[a.empleado_id] += total

    # Destajos
    total_destajos = Decimal("0")
    for r in RegistroDestajo.objects.filter(semana=semana).select_related("obra", "tipo"):
        r.total = Decimal(r.calcular_total())
        r.save(update_fields=["total"])
        total_destajos += r.total

    # Gastos de obra (insumos/viáticos)
    total_gastos = (GastoObra.objects
                    .filter(semana=semana)
                    .aggregate(s=Sum("monto"))["s"] or Decimal("0"))

    semana.total_sueldos = total_sueldos.quantize(Decimal("0.01"))
    semana.total_destajos = total_destajos.quantize(Decimal("0.01"))
    semana.total_gastos_obra = Decimal(total_gastos).quantize(Decimal("0.01"))
    semana.total_general = (semana.total_sueldos
                            + semana.total_destajos
                            + semana.total_gastos_obra).quantize(Decimal("0.01"))
    semana.save(update_fields=[
        "total_sueldos", "total_destajos", "total_gastos_obra", "total_general"
    ])
    return semana

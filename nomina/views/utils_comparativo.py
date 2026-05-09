from django.db.models import Sum
from .models import NominaEmpleado, NominaHistorial, NominaAcumulado
from datetime import datetime


def comparar_semanas(anio=None, proyecto=None):

    qs = NominaEmpleado.objects.select_related(
        "historial", "proyecto"
    )

    if anio:
        qs = qs.filter(historial__periodo_inicio__year=anio)

    if proyecto:
        qs = qs.filter(proyecto=proyecto)

    data = qs.values(
        "historial__periodo_inicio"
    ).annotate(
        total=Sum("total_neto")
    ).order_by("historial__periodo_inicio")

    return list(data)



def comparar_meses(anio=None, proyecto=None):

    qs = NominaAcumulado.objects.all()

    if anio:
        qs = qs.filter(anio=anio)

    if proyecto:
        qs = qs.filter(proyecto=proyecto)

    data = qs.values(
        "mes"
    ).annotate(
        total=Sum("importe")
    ).order_by("mes")

    return list(data)



def comparar_proyectos(anio=None):

    qs = NominaEmpleado.objects.select_related(
        "historial", "proyecto"
    )

    if anio:
        qs = qs.filter(historial__periodo_inicio__year=anio)

    data = qs.values(
        "proyecto__nombre"
    ).annotate(
        total=Sum("total_neto")
    ).order_by("proyecto__nombre")

    return list(data)

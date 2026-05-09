from datetime import timedelta, date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import ReporteEquipoPDA, ReporteEquipoDetalle, Equipo, Proyecto
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from finanzas.models import IngresoExtraordinario
from cxp.models import CompraEnc
from nomina.models import MovimientoCuentaProyecto
from django.http import HttpResponse





# ──────────────────────────────────────────────
#  Alertas (siempre 7 días fijos, tiempo real)
# ──────────────────────────────────────────────

def obtener_alertas_maquinaria():
    hoy   = timezone.localdate()
    hace7 = hoy - timedelta(days=7)
    ahora = timezone.now()
    alertas = []

    for j in ReporteEquipoPDA.objects.filter(estatus="ABIERTA").select_related("equipo", "usuario"):
        horas = (ahora - j.inicio).total_seconds() / 3600
        if horas > 12:
            alertas.append({
                "tipo": "danger",
                "titulo": "Jornada abierta excesiva",
                "detalle": f"{j.equipo} — {horas:.1f} h abierta. Usuario: {j.usuario.username}",
            })

    con_reporte = ReporteEquipoPDA.objects.filter(
        creado__date=hoy
    ).values_list("equipo_id", flat=True)
    for eq in Equipo.objects.filter(estado=True).exclude(id__in=con_reporte)[:10]:
        alertas.append({
            "tipo": "warning",
            "titulo": "Equipo sin reporte hoy",
            "detalle": f"{eq.descripcion} ({eq.placas}) sin jornada capturada",
        })

    for x in (
        ReporteEquipoDetalle.objects
        .filter(creado__date__gte=hace7, actividad__tipo="MUERTO")
        .values("reporte__equipo__descripcion")
        .annotate(total=Sum("horas"))
        .order_by("-total")[:10]
    ):
        if (x["total"] or 0) >= Decimal("4.00"):
            alertas.append({
                "tipo": "danger",
                "titulo": "Tiempo muerto alto",
                "detalle": f'{x["reporte__equipo__descripcion"]}: {x["total"]} h muertas en 7 días',
            })

    for x in (
        ReporteEquipoDetalle.objects
        .filter(creado__date__gte=hace7, actividad__tipo="MUERTO")
        .exclude(proyecto=None)
        .values("proyecto__nombre")
        .annotate(total=Sum("horas"))
        .order_by("-total")[:10]
    ):
        if (x["total"] or 0) >= Decimal("3.00"):
            alertas.append({
                "tipo": "warning",
                "titulo": "Proyecto con ineficiencia",
                "detalle": f'{x["proyecto__nombre"]}: {x["total"]} h muertas en 7 días',
            })

    for x in (
        ReporteEquipoDetalle.objects
        .filter(creado__date__gte=hace7, actividad__nombre__icontains="FALLA")
        .values("reporte__equipo__descripcion")
        .annotate(veces=Count("id"))
        .order_by("-veces")[:10]
    ):
        if x["veces"] >= 2:
            alertas.append({
                "tipo": "danger",
                "titulo": "Paros por falla repetidos",
                "detalle": f'{x["reporte__equipo__descripcion"]}: {x["veces"]} eventos en 7 días',
            })

    return alertas


# ──────────────────────────────────────────────
#  Score (siempre 7 días fijos)
# ──────────────────────────────────────────────

def obtener_score_operativo():
    hoy   = timezone.localdate()
    hace7 = hoy - timedelta(days=7)
    score = 100
    razones = []

    jornadas_abiertas = ReporteEquipoPDA.objects.filter(estatus="ABIERTA").count()
    if jornadas_abiertas > 0:
        score -= min(jornadas_abiertas * 5, 20)
        razones.append(f"{jornadas_abiertas} jornadas abiertas")

    tiempo_muerto = (
        ReporteEquipoDetalle.objects
        .filter(creado__date__gte=hace7, actividad__tipo="MUERTO")
        .aggregate(total=Sum("horas"))["total"] or Decimal("0.00")
    )
    if tiempo_muerto >= Decimal("10.00"):
        score -= 20
        razones.append(f"{tiempo_muerto} h muertas en 7 días")
    elif tiempo_muerto >= Decimal("5.00"):
        score -= 10
        razones.append(f"{tiempo_muerto} h muertas en 7 días")

    fallas = (
        ReporteEquipoDetalle.objects
        .filter(creado__date__gte=hace7, actividad__nombre__icontains="FALLA")
        .count()
    )
    if fallas >= 3:
        score -= 15
        razones.append(f"{fallas} paros por falla")

    score = max(score, 0)

    if score >= 85:
        nivel, color, icon = "SALUDABLE", "success", "fa-check-circle"
    elif score >= 65:
        nivel, color, icon = "ATENCION",  "warning", "fa-exclamation-circle"
    else:
        nivel, color, icon = "CRITICO",   "danger",  "fa-times-circle"

    return {"score": score, "nivel": nivel, "color": color, "icon": icon, "razones": razones}


# ──────────────────────────────────────────────
#  Jornadas activas (tiempo real)
# ──────────────────────────────────────────────

def obtener_jornadas_activas():
    ahora = timezone.now()
    jornadas = []
    for j in (
        ReporteEquipoPDA.objects
        .filter(estatus="ABIERTA")
        .select_related("equipo", "usuario")
        .order_by("inicio")
    ):
        horas = (ahora - j.inicio).total_seconds() / 3600
        alerta = "danger" if horas > 10 else ("warning" if horas > 8 else "success")
        jornadas.append({
            "equipo":  str(j.equipo),
            "usuario": j.usuario.username,
            "inicio":  j.inicio,
            "horas":   round(horas, 1),
            "alerta":  alerta,
        })
    return jornadas


# ──────────────────────────────────────────────
#  Eficiencia por equipo (período variable)
# ──────────────────────────────────────────────

def obtener_eficiencia_equipos(fecha_inicio, fecha_fin):
    base = ReporteEquipoDetalle.objects.filter(
        creado__date__gte=fecha_inicio,
        creado__date__lte=fecha_fin,
    )
    totales = (
        base
        .values("reporte__equipo__descripcion")
        .annotate(horas_total=Sum("horas"))
    )
    muertos_dict = {
        x["reporte__equipo__descripcion"]: x["horas_muertas"]
        for x in base.filter(actividad__tipo="MUERTO")
        .values("reporte__equipo__descripcion")
        .annotate(horas_muertas=Sum("horas"))
    }
    resultado = []
    for row in totales.order_by("-horas_total")[:15]:
        equipo        = row["reporte__equipo__descripcion"]
        horas_total   = row["horas_total"] or Decimal("0")
        horas_muertas = muertos_dict.get(equipo, Decimal("0")) or Decimal("0")
        horas_prod    = horas_total - horas_muertas
        eficiencia    = int((horas_prod / horas_total) * 100) if horas_total > 0 else 0
        color = "success" if eficiencia >= 85 else ("warning" if eficiencia >= 65 else "danger")
        resultado.append({
            "equipo":            equipo,
            "horas_total":       round(horas_total, 1),
            "horas_muertas":     round(horas_muertas, 1),
            "horas_productivas": round(horas_prod, 1),
            "eficiencia":        eficiencia,
            "color":             color,
        })
    return resultado


# ──────────────────────────────────────────────
#  Helper: queries por rango
# ──────────────────────────────────────────────

def _queries_por_rango(fecha_inicio, fecha_fin):
    detalles = ReporteEquipoDetalle.objects.select_related(
        "actividad", "reporte__equipo", "proyecto"
    ).filter(
        creado__date__gte=fecha_inicio,
        creado__date__lte=fecha_fin,
    )
    return {
        "top_proyectos": (
            detalles.values("proyecto__nombre")
            .annotate(total=Sum("horas"))
            .order_by("-total")[:10]
        ),
        "top_equipos": (
            detalles.values("reporte__equipo__descripcion")
            .annotate(total=Sum("horas"))
            .order_by("-total")[:10]
        ),
        "tiempos_muertos": (
            detalles.filter(actividad__tipo="MUERTO")
            .values("proyecto__nombre")
            .annotate(total=Sum("horas"))
            .order_by("-total")[:10]
        ),
        "actividades": (
            detalles.values("actividad__nombre")
            .annotate(total=Sum("horas"))
            .order_by("-total")[:10]
        ),
    }


# ──────────────────────────────────────────────
#  Vista principal
# ──────────────────────────────────────────────

@login_required
def dashboard_maquinaria(request):
    hoy   = timezone.localdate()
    hace7 = hoy - timedelta(days=7)

    # ── Filtro de fechas desde GET ────────────
    try:
        fecha_inicio = date.fromisoformat(request.GET.get("fecha_inicio", ""))
    except (ValueError, TypeError):
        fecha_inicio = hace7

    try:
        fecha_fin = date.fromisoformat(request.GET.get("fecha_fin", ""))
    except (ValueError, TypeError):
        fecha_fin = hoy

    if fecha_inicio > fecha_fin:
        fecha_inicio, fecha_fin = fecha_fin, fecha_inicio

    # ── KPIs de hoy (siempre tiempo real) ────
    hoy_qs = ReporteEquipoDetalle.objects.filter(reporte__creado__date=hoy)
    horas_hoy        = hoy_qs.aggregate(total=Sum("horas"))["total"] or 0
    equipos_activos  = ReporteEquipoPDA.objects.filter(estatus="ABIERTA").count()
    proyectos_activos = (
        hoy_qs.exclude(proyecto=None).values("proyecto").distinct().count()
    )

    # ── Datos fijos 7 días para pestaña Resumen ──
    datos_default = _queries_por_rango(hace7, hoy)

    # ── Datos del período para pestaña Análisis ──
    datos_periodo = _queries_por_rango(fecha_inicio, fecha_fin)

    context = {
        # Filtro activo
        "fecha_inicio":          fecha_inicio,
        "fecha_fin":             fecha_fin,
        # KPIs hoy
        "horas_hoy":             horas_hoy,
        "equipos_activos":       equipos_activos,
        "proyectos_activos":     proyectos_activos,
        # Pestaña Resumen (7 días fijos)
        "top_proyectos_default": datos_default["top_proyectos"],
        "top_equipos_default":   datos_default["top_equipos"],
        "tiempos_muertos_default": datos_default["tiempos_muertos"],
        "actividades_default":   datos_default["actividades"],
        # Pestaña Análisis (período variable)
        "top_proyectos":         datos_periodo["top_proyectos"],
        "top_equipos":           datos_periodo["top_equipos"],
        "tiempos_muertos":       datos_periodo["tiempos_muertos"],
        "actividades":           datos_periodo["actividades"],
        "eficiencia_equipos":    obtener_eficiencia_equipos(fecha_inicio, fecha_fin),
        # Pestaña Jornadas
        "jornadas_activas":      obtener_jornadas_activas(),
        # Score y alertas
        "score_operativo":       obtener_score_operativo(),
        "alertas_maquinaria":    obtener_alertas_maquinaria(),
    }

    return render(request, "adm/dashboard_maquinaria.html", context)


def proyecto_tablero(request, pk):

    proyecto = get_object_or_404(Proyecto, pk=pk)

    context = {
        "proyecto": proyecto,
        "finanzas": resumen_finanzas(proyecto),
        "actividades": resumen_actividades(proyecto),
        "clientes": resumen_clientes(proyecto),
    }

    return render(request, "adm/proyecto_360.html", context)

def resumen_finanzas(proyecto):

    ingresos = IngresoExtraordinario.objects.filter(
        proyecto=proyecto
    ).aggregate(total=Sum("importe"))["total"] or 0

    compras = Compra.objects.filter(
        proyecto=proyecto
    ).aggregate(total=Sum("total"))["total"] or 0

    nomina = NominaDetalle.objects.filter(
        proyecto=proyecto
    ).aggregate(total=Sum("importe"))["total"] or 0

    egresos = compras + nomina

    return {
        "ingresos": ingresos,
        "egresos": egresos,
        "utilidad": ingresos - egresos
    }    


def resumen_actividades(proyecto):

    return ReporteEquipoDetalle.objects.filter(
        proyecto=proyecto
    ).select_related("actividad", "usuario")[:10]


def resumen_clientes(proyecto):

    return Cliente.objects.filter(
        rentaequipo__proyecto=proyecto
    ).distinct()[:10]        






class Proyecto360View(LoginRequiredMixin, DetailView):
    model = Proyecto
    template_name = "adm/proyecto_tablero.html"
    context_object_name = "proyecto"

    def get_queryset(self):
        return Proyecto.objects.only(
            "id",
            "nombre",
            "estado",
        )    




@login_required
def proyecto360_finanzas_ajax(request, pk):

    proyecto = get_object_or_404(
        Proyecto,
        pk=pk
    )

    presupuesto = proyecto.presupuesto or 0

    compras_total = (
        CompraEnc.objects
        .filter(
            proyecto_id=proyecto.id
        )
        .aggregate(total=Sum("total"))
        .get("total") or 0
    )

    nomina_total = (
        MovimientoCuentaProyecto.objects
        .filter(proyecto=proyecto)
        .aggregate(total=Sum("importe"))
        .get("total") or 0
    )

    

    egresos = compras_total + nomina_total

    disponible = presupuesto - egresos

    porcentaje = 0

    if presupuesto > 0:
        porcentaje = (egresos / presupuesto) * 100

    print("COMPRAS TOTAL:", compras_total)
    print("NOMINA TOTAL:", nomina_total)
    print("EGRESOS:", egresos)        

    context = {
        "presupuesto": presupuesto,
        "egresos": egresos,
        "disponible": disponible,
        "porcentaje": porcentaje,
    }

    return render(
        request,
        "adm/partials/_finanzas.html",
        context
    )


@login_required
def proyecto360_compras_ajax(request, pk):

    try:

        proyecto = get_object_or_404(
            Proyecto,
            pk=pk
        )

        ultimas_compras = (
            CompraEnc.objects
            .filter(proyecto_id=proyecto.id)
            .order_by("-fecha")[:5]
        )

        context = {
            "proyecto": proyecto,
            "ultimas_compras": ultimas_compras,
        }

        return render(
            request,
            "adm/partials/_compras.html",
            context
        )

    except Exception as e:

        return HttpResponse(
            f"<div class='alert alert-danger'>"
            f"ERROR COMPRAS: {e}"
            f"</div>"
        )



def proyecto360_nomina_ajax(request, pk):

    proyecto = get_object_or_404(Proyecto, pk=pk)

    base_qs = (
        MovimientoCuentaProyecto.objects
        .filter(proyecto=proyecto)
    )

    movimientos = (
        base_qs
        .select_related("empleado", "periodo")
        .order_by("-fecha")[:15]
    )

    empleados = (
        base_qs
        .values("empleado")
        .distinct()
        .count()
    )

    total_nomina = base_qs.aggregate(
        total=Sum("importe")
    )["total"] or 0

    context = {
        "proyecto": proyecto,
        "movimientos": movimientos,
        "total_nomina": total_nomina,
        "empleados": empleados,
    }

    return render(
        request,
        "adm/partials/_nomina.html",
        context
    )        
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import ReporteEquipoDetalle, Equipo, Proyecto, ActividadEquipo, ReporteEquipoPDA, ReporteEquipo
from django.utils.dateparse import parse_date
from .utils import es_admin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils.dateparse import parse_date
from datetime import datetime, date, time
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from .views_pda import combinar_hora_con_fecha, horas_entre

@login_required
def oficina_actividades(request):

    if not es_admin(request.user):
        return render(request, "base/403.html")

    qs = ReporteEquipoDetalle.objects.select_related(
        "usuario", "actividad", "reporte"
    ).order_by("-creado")

    # 🔍 filtros
    operador = request.GET.get("operador")
    fecha = request.GET.get("fecha")

    if operador:
        qs = qs.filter(usuario_id=operador)

    if fecha:
        fecha = parse_date(fecha)
        if fecha:
            qs = qs.filter(creado__date=fecha)

    return render(request, "adm/oficina_actividades.html", {
        "datos": qs
    })


from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.utils import timezone
from .forms import ActividadDetalleForm


@login_required
def editar_actividad(request, pk):

    obj = get_object_or_404(ReporteEquipoDetalle, pk=pk)

    if not es_admin(request.user):
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        form = ActividadDetalleForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)

            # 🔥 auditoría
            obj.editado_por = request.user
            obj.editado_en = timezone.now()

            obj.save()
            return redirect("adm:oficina_actividades")

    else:
        form = ActividadDetalleForm(instance=obj)

    if form.is_valid():
        obj = form.save(commit=False)

        if obj.inicio_dt and obj.fin_dt:
            delta = obj.fin_dt - obj.inicio_dt
            obj.horas = round(delta.total_seconds() / 3600, 2)

        obj.editado_por = request.user
        obj.editado_en = timezone.now()
        obj = form.save(commit=False)


        obj.save()

    return render(request, "adm/editar_actividad.html", {
        "form": form
    })    
    
# ── Agregar a views_pda.py o views_oficina.py ─────────────────────────────────

from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils.dateparse import parse_date
import json


# ══════════════════════════════════════════════════════════════════════════════
# LISTADO DE ACTIVIDADES — todos los operadores
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def listado_actividades(request):
    """
    Vista para admin y usuarios de oficina.
    Muestra ReporteEquipoDetalle con filtros y totales por operador.
    """
    from .utils import es_admin  # ajusta si tu helper está en otro lugar

    # Cualquier usuario autenticado puede ver (admin o usuario de oficina)
    # Si quieres restringir solo a admin, descomenta:
    # if not es_admin(request.user):
    #     return render(request, "base/403.html")

    # ── Filtros GET ────────────────────────────────────────────────────────────
    fecha_inicio_str = request.GET.get("fecha_inicio", "")
    fecha_fin_str    = request.GET.get("fecha_fin", "")
    equipo_id        = request.GET.get("equipo", "")
    operador_id      = request.GET.get("operador", "")
    proyecto_id      = request.GET.get("proyecto", "")

    qs = (
        ReporteEquipoDetalle.objects
        .select_related(
            "actividad",
            "proyecto",
            "usuario",
            "reporte",
            "reporte__equipo",
        )
        .order_by("-inicio")
    )

    # Fechas
    fecha_inicio = parse_date(fecha_inicio_str) if fecha_inicio_str else None
    fecha_fin    = parse_date(fecha_fin_str)    if fecha_fin_str    else None

    if fecha_inicio:
        qs = qs.filter(inicio__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(inicio__date__lte=fecha_fin)

    # Equipo
    if equipo_id:
        qs = qs.filter(reporte__equipo_id=equipo_id)

    # Operador
    if operador_id:
        qs = qs.filter(usuario_id=operador_id)

    # Proyecto
    if proyecto_id:
        qs = qs.filter(proyecto_id=proyecto_id)

    # ── Totales por operador ───────────────────────────────────────────────────
    totales_operador = (
        qs.values(
            "usuario__id",
            "usuario__username",
            "usuario__first_name",
            "usuario__last_name",
        )
        .annotate(
            total_horas    = Sum("horas"),
            total_registros = Count("id"),
        )
        .order_by("-total_horas")
    )

    # ── Catálogos para filtros ─────────────────────────────────────────────────
    equipos    = Equipo.objects.filter(estado=True).order_by("descripcion")
    operadores = User.objects.filter(
        reporteequipodetalle__isnull=False
    ).distinct().order_by("username")
    proyectos  = Proyecto.objects.filter(estado=True).order_by("nombre")

    return render(request, "adm/listado_actividades.html", {
        "registros":         qs,
        "totales_operador":  totales_operador,
        "equipos":           equipos,
        "operadores":        operadores,
        "proyectos":         proyectos,
        # Valores actuales de filtros para repintar el form
        "f_fecha_inicio":    fecha_inicio_str,
        "f_fecha_fin":       fecha_fin_str,
        "f_equipo":          equipo_id,
        "f_operador":        operador_id,
        "f_proyecto":        proyecto_id,
    })


# ══════════════════════════════════════════════════════════════════════════════
# CAPTURA BLOQUES OFICINA — sin jornada, admin elige equipo y fecha
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def captura_bloques_oficina(request):
    """
    Captura de bloques para admin sin necesidad de jornada abierta.
    El admin elige equipo, operador y fecha libremente.
    """
    from .utils import es_admin

    if not es_admin(request.user):
        return render(request, "base/403.html")

    equipos    = Equipo.objects.filter(estado=True).order_by("descripcion")
    proyectos  = Proyecto.objects.filter(estado=True).order_by("nombre")
    operadores = User.objects.filter(is_active=True).order_by("username")
    actividades = ActividadEquipo.objects.filter(activo=True).order_by("nombre")

    # Historial reciente para mostrar en la misma pantalla
    # Filtra por los parámetros GET si vienen de una captura previa
    equipo_sel   = request.GET.get("equipo_id", "")
    fecha_sel    = request.GET.get("fecha", "")
    operador_sel = request.GET.get("operador_id", "")

    historial = ReporteEquipoDetalle.objects.none()

    if equipo_sel and fecha_sel:
        historial = (
            ReporteEquipoDetalle.objects
            .filter(
                reporte__equipo_id=equipo_sel,
                inicio__date=parse_date(fecha_sel),
            )
            .select_related("actividad", "proyecto", "usuario", "reporte__equipo")
            .order_by("inicio")
        )

    return render(request, "adm/captura_bloques_oficina.html", {
        "equipos":    equipos,
        "proyectos":  proyectos,
        "operadores": operadores,
        "actividades": actividades,
        "historial":  historial,
        "equipo_sel":   equipo_sel,
        "fecha_sel":    fecha_sel,
        "operador_sel": operador_sel,
    })


@login_required
@transaction.atomic
def guardar_bloques_oficina(request):
    """
    Guarda bloques capturados por el admin sin jornada.
    Crea una jornada temporal si no existe para esa fecha/equipo/usuario.
    """
    from .utils import es_admin

    if not es_admin(request.user):
        return JsonResponse({"ok": False, "msg": "No autorizado"})

    if request.method != "POST":
        return JsonResponse({"ok": False, "msg": "Método no permitido"})

    data = json.loads(request.body or "{}")

    bloques      = data.get("bloques", [])
    equipo_id    = data.get("equipo_id")
    operador_id  = data.get("operador_id")
    fecha_str    = data.get("fecha")

    if not bloques:
        return JsonResponse({"ok": False, "msg": "Sin bloques"})
    if not equipo_id:
        return JsonResponse({"ok": False, "msg": "Equipo requerido"})
    if not operador_id:
        return JsonResponse({"ok": False, "msg": "Operador requerido"})
    if not fecha_str:
        return JsonResponse({"ok": False, "msg": "Fecha requerida"})

    fecha_base = parse_date(fecha_str)
    if not fecha_base:
        return JsonResponse({"ok": False, "msg": "Fecha inválida"})

    try:
        operador = User.objects.get(id=operador_id)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "msg": "Operador no encontrado"})

    # ── Busca o crea jornada para esa fecha/equipo/operador ───────────────────
    # Busca jornada existente ese día para ese equipo y operador
    inicio_dia = timezone.make_aware(
        datetime.combine(fecha_base, datetime.min.time()),
        timezone.get_current_timezone()
    )
    fin_dia = timezone.make_aware(
        datetime.combine(fecha_base, datetime.max.time()),
        timezone.get_current_timezone()
    )

    jornada = (
        ReporteEquipoPDA.objects
        .filter(
            usuario=operador,
            equipo_id=equipo_id,
            inicio__gte=inicio_dia,
            inicio__lte=fin_dia,
        )
        .first()
    )

    if not jornada:
        # Crea jornada administrativa cerrada para esa fecha
        jornada = ReporteEquipoPDA.objects.create(
            usuario=operador,
            equipo_id=equipo_id,
            inicio=inicio_dia,
            fin=fin_dia,
            estatus="CERRADA",  # ya cerrada — no interfiere con el PDA
        )

    # ── Guarda los bloques ────────────────────────────────────────────────────
    from datetime import datetime as dt, date as dt_date, time as dt_time
    from datetime import datetime as datetime_cls

    creados   = 0
    omitidos  = 0
    errores   = []

    for b in bloques:
        actividad_id = b.get("actividad_id")
        proyecto_id  = b.get("proyecto_id") or None
        inicio_txt   = b.get("inicio")
        fin_txt      = b.get("fin")
        obs          = b.get("obs", "")

        if not actividad_id or not inicio_txt or not fin_txt:
            omitidos += 1
            continue

        try:
            inicio_dt = combinar_hora_con_fecha(fecha_base, inicio_txt)
            fin_dt    = combinar_hora_con_fecha(fecha_base, fin_txt)
        except Exception:
            errores.append(f"Hora inválida: {inicio_txt} - {fin_txt}")
            continue

        if fin_dt <= inicio_dt:
            errores.append(f"Fin ({fin_txt}) debe ser mayor que inicio ({inicio_txt})")
            continue

        horas = horas_entre(inicio_dt, fin_dt)

        ReporteEquipoDetalle.objects.create(
            reporte=jornada,
            usuario=operador,
            actividad_id=actividad_id,
            proyecto_id=proyecto_id,
            inicio=inicio_dt,
            fin=fin_dt,
            horas=horas,
            observaciones=obs,
        )
        creados += 1

    return JsonResponse({
        "ok":      True,
        "insertados": creados,
        "omitidos":   omitidos,
        "errores":    errores,
        "equipo_id":   equipo_id,
        "fecha":       fecha_str,
        "operador_id": operador_id,
    })


# ══════════════════════════════════════════════════════════════════════════════
# HISTORIAL AJAX — para cargar historial sin recargar página
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def historial_bloques_ajax(request):
    from .utils import es_admin
    from django.utils.dateparse import parse_date

    if not es_admin(request.user):
        return JsonResponse({"ok": False, "msg": "No autorizado"})

    equipo_id   = request.GET.get("equipo_id")
    fecha_str   = request.GET.get("fecha")
    operador_id = request.GET.get("operador_id")

    if not equipo_id or not fecha_str:
        return JsonResponse({"ok": False, "msg": "Parámetros incompletos"})

    fecha = parse_date(fecha_str)
    if not fecha:
        return JsonResponse({"ok": False, "msg": "Fecha inválida"})

    qs = (
        ReporteEquipoDetalle.objects
        .filter(
            reporte__equipo_id=equipo_id,
            inicio__date=fecha,
        )
        .select_related("actividad", "proyecto", "usuario")
        .order_by("inicio")
    )

    if operador_id:
        qs = qs.filter(usuario_id=operador_id)

    registros = [
        {
            "actividad": r.actividad.nombre,
            "tipo":      r.actividad.tipo,
            "proyecto":  r.proyecto.nombre if r.proyecto else None,
            "operador":  r.usuario.get_full_name() or r.usuario.username,
            "inicio":    r.inicio.strftime("%H:%M"),
            "fin":       r.fin.strftime("%H:%M") if r.fin else None,
            "horas":     str(r.horas),
        }
        for r in qs
    ]

    return JsonResponse({"ok": True, "registros": registros})    






@login_required
def actividades_por_equipo_ajax(request):
    from .utils import es_admin
    if not es_admin(request.user):
        return JsonResponse({"ok": False})

    equipo_id = request.GET.get("equipo_id")
    if not equipo_id:
        return JsonResponse({"ok": True, "actividades": []})

    try:
        equipo = Equipo.objects.get(id=equipo_id)
    except Equipo.DoesNotExist:
        return JsonResponse({"ok": False, "actividades": []})

    if not equipo.tipo_equipo:
        # Si el equipo no tiene tipo, devuelve todas las activas
        actividades = ActividadEquipo.objects.filter(activo=True).order_by("nombre")
    else:
        actividades = (
            ActividadEquipo.objects
            .filter(activo=True, tipos_equipo=equipo.tipo_equipo)
            .order_by("nombre")
        )

    return JsonResponse({
        "ok": True,
        "actividades": [
            {"id": a.id, "nombre": a.nombre, "tipo": a.tipo}
            for a in actividades
        ]
    })
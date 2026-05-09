# views_pda.py  --- VERSION PRO / DATETIME REAL / PRODUCCION

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from decimal import Decimal
from datetime import datetime

import json

from .models import (
    ReporteEquipoPDA,
    ReporteEquipoDetalle,
    ActividadEquipo,
    Equipo,
    Proyecto,
)


# ==========================================================
# HELPERS
# ==========================================================

def ahora():
    return timezone.now()


def hoy():
    return timezone.localdate()


def horas_entre(inicio, fin):
    if not inicio or not fin:
        return Decimal("0.00")

    segundos = (fin - inicio).total_seconds()

    if segundos < 0:
        return Decimal("0.00")

    return Decimal(segundos / 3600).quantize(Decimal("0.01"))


def combinar_hora_con_fecha(fecha_base, hora_txt):
    """
    '08:30' -> datetime aware
    """
    naive = datetime.strptime(
        f"{fecha_base} {hora_txt}",
        "%Y-%m-%d %H:%M"
    )

    return timezone.make_aware(
        naive,
        timezone.get_current_timezone()
    )


def obtener_jornada_abierta(usuario):
    return (
        ReporteEquipoPDA.objects
        .filter(
            usuario=usuario,
            estatus="ABIERTA"
        )
        .select_related(
            "equipo",
            "equipo__tipo_equipo"
        )
        .order_by("-id")
        .first()
    )


def obtener_actividades_por_jornada(jornada):
    if not jornada:
        return ActividadEquipo.objects.none()

    if not jornada.equipo:
        return ActividadEquipo.objects.none()

    if not jornada.equipo.tipo_equipo:
        return ActividadEquipo.objects.none()

    return (
        ActividadEquipo.objects
        .filter(
            activo=True,
            tipos_equipo=jornada.equipo.tipo_equipo
        )
        .distinct()
        .order_by("nombre")
    )


def cerrar_actividad_abierta(jornada, momento=None):

    if not momento:
        momento = ahora()

    detalle = (
        ReporteEquipoDetalle.objects
        .filter(
            reporte=jornada,
            fin__isnull=True
        )
        .order_by("-id")
        .first()
    )

    if not detalle:
        return None

    detalle.fin = momento
    detalle.horas = horas_entre(
        detalle.inicio,
        detalle.fin
    )

    detalle.save(
        update_fields=["fin", "horas"]
    )

    return detalle


# ==========================================================
# INICIO
# ==========================================================

@login_required
def pda_inicio(request):

    jornada = obtener_jornada_abierta(request.user)

    if jornada:
        return redirect("adm:pda_mobile_operacion")

    equipos = (
        Equipo.objects
        .filter(estado=True)
        .order_by("descripcion")
    )

    return render(
        request,
        "adm/pda/mobile_inicio.html",
        {
            "equipos": equipos
        }
    )



@login_required
def pda_menu(request):
    jornada = obtener_jornada_abierta(request.user)

    if jornada:
        return redirect("adm:captura_bloques")

    return render(request, "adm/pda/menu.html")



@login_required
@transaction.atomic
def cerrar_jornada_escritorio(request):
    return terminar_jornada(request)


@login_required
def jornada_escritorio(request):
    jornada = obtener_jornada_abierta(request.user)

    if not jornada:
        return redirect("adm:pda_inicio")

    actividades = obtener_actividades_por_jornada(jornada)

    detalles = ReporteEquipoDetalle.objects.filter(
        reporte=jornada
    ).select_related(
        "actividad",
        "proyecto"
    ).order_by("-inicio", "-creado")

    return render(
        request,
        "adm/pda/jornada_escritorio.html",
        {
            "jornada": jornada,
            "actividades": actividades,
            "detalles": detalles,
        }
    )


# @login_required
# def pda_mobile_inicio(request):
#     jornada = obtener_jornada_abierta(request.user)

#     if jornada:
#         return redirect("adm:pda_mobile_operacion")

#     equipos = Equipo.objects.filter(estado=True).order_by("descripcion")

#     return render(request, "adm/pda/mobile_inicio.html", {
#         "equipos": equipos,
#     })


@login_required
def pda_mobile_inicio(request):

    jornada = obtener_jornada_abierta(request.user)

    if jornada:
        return redirect("adm:pda_mobile_operacion")

    if request.method == "POST":

        equipo_id = request.POST.get("equipo")

        if not equipo_id:

            messages.warning(
                request,
                "Seleccione un equipo"
            )

            return redirect("adm:pda_inicio")

        ReporteEquipoPDA.objects.create(
            usuario=request.user,
            equipo_id=equipo_id,
            inicio=timezone.now(),
            estatus="ABIERTA"
        )

        return redirect("adm:pda_mobile_operacion")

    equipos = (
        Equipo.objects
        .filter(estado=True)
        .order_by("descripcion")
    )

    return render(
        request,
        "adm/pda/mobile_inicio.html",
        {
            "equipos": equipos,
        }
    )



@login_required
def iniciar_actividad_escritorio(request):
    return iniciar_actividad(request)

# ==========================================================
# ABRIR JORNADA
# ==========================================================

@login_required
@transaction.atomic
def iniciar_jornada(request):

    if request.method != "POST":
        return redirect("adm:pda_inicio")

    equipo_id = request.POST.get("equipo")

    if not equipo_id:
        messages.warning(request, "Seleccione equipo")
        return redirect("adm:pda_inicio")

    # 🔥 Validar jornada activa del operador
    activa = ReporteEquipoPDA.objects.filter(
        usuario=request.user,
        estatus="ABIERTA"
    ).first()

    if activa:
        return redirect("adm:pda_mobile_operacion")

    # 🔥 Validar equipo ocupado
    equipo_ocupado = ReporteEquipoPDA.objects.filter(
        equipo_id=equipo_id,
        estatus="ABIERTA"
    ).exists()

    if equipo_ocupado:
        messages.error(request, "El equipo ya está en uso")
        return redirect("adm:pda_inicio")

    # 🔥 Crear jornada
    ReporteEquipoPDA.objects.create(
        usuario=request.user,
        equipo_id=equipo_id,
        inicio=timezone.now(),
        estatus="ABIERTA"
    )

    messages.success(request, "Jornada iniciada")

    return redirect("adm:pda_mobile_operacion")

# ==========================================================
# CERRAR JORNADA
# ==========================================================

@login_required
@transaction.atomic
def terminar_jornada(request):

    if request.method != "POST":
        return redirect("adm:pda_inicio")

    jornada = (
        ReporteEquipoPDA.objects
        .select_for_update()
        .filter(
            usuario=request.user,
            estatus="ABIERTA"
        )
        .order_by("-id")
        .first()
    )

    if not jornada:
        messages.warning(
            request,
            "No existe jornada abierta"
        )
        return redirect("adm:pda_inicio")

    momento = ahora()

    cerrar_actividad_abierta(
        jornada,
        momento
    )

    total = (
        jornada.detalles
        .aggregate(
            t=Sum("horas")
        )["t"]
        or Decimal("0.00")
    )

    jornada.fin = momento
    jornada.estatus = "CERRADA"
    jornada.save(
        update_fields=["fin", "estatus"]
    )

    messages.success(
        request,
        f"Jornada cerrada ({total} hrs)"
    )

    return redirect("adm:pda_inicio")


# ==========================================================
# PANTALLA OPERACION
# ==========================================================

@login_required
def pda_mobile_operacion(request):

    jornada = obtener_jornada_abierta(
        request.user
    )

    if not jornada:
        return redirect("adm:pda_inicio")

    actividades = obtener_actividades_por_jornada(
        jornada
    )

    actividad_actual = (
        jornada.detalles
        .filter(fin__isnull=True)
        .select_related("actividad")
        .order_by("-id")
        .first()
    )

    detalles = (
        jornada.detalles
        .select_related(
            "actividad",
            "proyecto"
        )
        .order_by("-id")[:10]
    )

    

    ultimo = ReporteEquipoDetalle.objects.filter(
        usuario=request.user
    ).order_by("-creado").first()

    ultimo_proyecto = ultimo.proyecto if ultimo else None    

    proyectos = Proyecto.objects.all()

    return render(
        request,
        "adm/pda/mobile_operacion.html",
        {
            "jornada": jornada,
            "actividades": actividades,
            "actividad_actual": actividad_actual,
            "detalles_hoy": detalles,
            "proyectos":proyectos,
            "ultimo_proyecto": ultimo_proyecto,   
        }
    )


# ==========================================================
# INICIAR ACTIVIDAD AJAX
# ==========================================================

@login_required
@transaction.atomic
def iniciar_actividad(request):

    if request.method != "POST":
        return JsonResponse({
            "ok": False
        })

    data = json.loads(
        request.body or "{}"
    )

    actividad_id = data.get(
        "actividad_id"
    )
    proyecto_id = data.get("proyecto_id")
    print("PROYECTO_ID:", proyecto_id)

    jornada = obtener_jornada_abierta(
        request.user
    )

    if not jornada:
        return JsonResponse({
            "ok": False,
            "msg": "Sin jornada"
        })

    valida = (
        obtener_actividades_por_jornada(
            jornada
        )
        .filter(id=actividad_id)
        .exists()
    )

    if not proyecto_id:
        return JsonResponse({
            "ok": False,
            "msg": "Proyecto requerido"
        })

    if not valida:
        return JsonResponse({
            "ok": False,
            "msg": "Actividad inválida"
        })

    momento = ahora()

    cerrar_actividad_abierta(
        jornada,
        momento
    )

    ReporteEquipoDetalle.objects.create(
        reporte=jornada,
        usuario=request.user,
        actividad_id=actividad_id,
        proyecto_id=proyecto_id,
        inicio=momento
    )

    return JsonResponse({
        "ok": True
    })


# ==========================================================
# CAPTURA BLOQUES
# ==========================================================

@login_required
def captura_bloques(request):

    jornada = obtener_jornada_abierta(
        request.user
    )

    if not jornada:
        return redirect("adm:pda_inicio")

    actividades = obtener_actividades_por_jornada(
        jornada
    )

    detalles = (
        jornada.detalles
        .select_related(
            "actividad",
            "proyecto"
        )
        .order_by("inicio")
    )

    proyectos = (
        Proyecto.objects
        .filter(estado=True)
        .order_by("nombre")
    )

    return render(
        request,
        "adm/pda/captura_bloques.html",
        {
            "jornada": jornada,
            "actividades": actividades,
            "detalles": detalles,
            "proyectos": proyectos,
        }
    )


@login_required
@transaction.atomic
def guardar_bloques(request):

    jornada = obtener_jornada_abierta(
        request.user
    )

    if not jornada:
        return JsonResponse({
            "ok": False,
            "msg": "Sin jornada"
        })

    data = json.loads(
        request.body or "{}"
    )

    bloques = data.get(
        "bloques",
        []
    )

    if not bloques:
        return JsonResponse({
            "ok": False,
            "msg": "Sin datos"
        })

    fecha_base = hoy()

    creados = 0

    for b in bloques:

        actividad_id = b.get(
            "actividad_id"
        )

        inicio_txt = b.get("inicio")
        fin_txt = b.get("fin")

        proyecto_id = (
            b.get("proyecto_id")
            or None
        )

        obs = b.get("obs", "")

        if not actividad_id:
            continue

        if not inicio_txt:
            continue

        if not fin_txt:
            continue

        inicio_dt = combinar_hora_con_fecha(
            fecha_base,
            inicio_txt
        )

        fin_dt = combinar_hora_con_fecha(
            fecha_base,
            fin_txt
        )

        if fin_dt <= inicio_dt:
            continue

        horas = horas_entre(
            inicio_dt,
            fin_dt
        )

        ReporteEquipoDetalle.objects.create(
            reporte=jornada,
            usuario=request.user,
            actividad_id=actividad_id,
            proyecto_id=proyecto_id,
            inicio=inicio_dt,
            fin=fin_dt,
            horas=horas,
            observaciones=obs
        )

        creados += 1

    return JsonResponse({
        "ok": True,
        "creados": creados
    })


# ==========================================================
# DASHBOARD
# ==========================================================

@login_required
def dashboard_maquinaria(request):

    registros = (
        ReporteEquipoDetalle.objects
        .filter(
            creado__date=hoy()
        )
        .select_related(
            "actividad",
            "reporte",
            "reporte__equipo"
        )
    )

    productivas = (
        registros
        .filter(
            actividad__tipo="PRODUCTIVO"
        )
        .aggregate(
            t=Sum("horas")
        )["t"]
        or 0
    )

    muertas = (
        registros
        .filter(
            actividad__tipo="MUERTO"
        )
        .aggregate(
            t=Sum("horas")
        )["t"]
        or 0
    )

    abiertas = (
        ReporteEquipoPDA.objects
        .filter(
            estatus="ABIERTA"
        )
        .count()
    )

    return render(
        request,
        "adm/dashboard_maquinaria.html",
        {
            "productivas": productivas,
            "muertas": muertas,
            "abiertas": abiertas,
        }
    )


@login_required
def mis_movimientos(request):

    qs = ReporteEquipoPDA.objects.filter(
        usuario=request.user
    ).order_by("-id")

    if request.user.is_superuser:
        qs = ReporteEquipoPDA.objects.all().order_by("-id")

    return render(request,"adm/pda/mis_movimientos.html",{
        "datos": qs
    })    
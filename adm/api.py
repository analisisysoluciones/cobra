from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from decimal import Decimal
from datetime import datetime
import logging

from adm.models import Equipo, CargaCombustible

logger = logging.getLogger(__name__)

def usuario_puede_usar_pda(user):
    return (
        user.is_superuser or
        user.groups.filter(name__in=["Operadores", "Administradores"]).exists()
    )


    
# =====================================================
# API EQUIPOS
# =====================================================
@login_required
def api_equipos_activos(request):

    if not usuario_puede_usar_pda(request.user):
        return HttpResponseForbidden("No autorizado")

    equipos = Equipo.objects.filter(estado=True).values(
        "id",
        "identificador",
        "descripcion",
        "placas"
    )

    return JsonResponse(list(equipos), safe=False)


# =====================================================
# CAPTURA COMBUSTIBLE (FLUJO CORRECTO)
# =====================================================
@ensure_csrf_cookie
@login_required
def captura_combustible(request):

    if not usuario_puede_usar_pda(request.user):
        return HttpResponseForbidden("No autorizado")

    # =========================
    # GET
    # =========================
    if request.method == "GET":
        return render(request, "flotilla/captura.html")

    # =========================
    # POST
    # =========================
    try:
        # -------------------------
        # VALIDACIONES BASICAS
        # -------------------------
        equipo_id = request.POST.get("equipo_id")
        if not equipo_id:
            raise ValueError("Selecciona un vehículo")

        equipo = get_object_or_404(Equipo, id=equipo_id)

        fecha_str = request.POST.get("fecha_carga")
        if not fecha_str:
            raise ValueError("Fecha obligatoria")

        try:
            fecha_carga = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except:
            raise ValueError("Formato de fecha inválido")

        if fecha_carga > timezone.now().date():
            raise ValueError("La fecha no puede ser mayor a hoy")

        folio = (request.POST.get("folio") or "").strip().upper()
        if not folio:
            raise ValueError("El folio es obligatorio")

        # -------------------------
        # DUPLICADOS
        # -------------------------
        if CargaCombustible.objects.filter(
            equipo=equipo,
            fecha_carga=fecha_carga,
            folio=folio
        ).exists():
            raise ValueError("Ya existe una carga con ese folio para ese equipo")

        # -------------------------
        # NUMERICOS
        # -------------------------
        try:
            litros = Decimal(request.POST.get("cantidad_litros"))
        except:
            raise ValueError("Litros inválidos")

        try:
            precio = Decimal(request.POST.get("precio_litro"))
        except:
            raise ValueError("Precio inválido")

        if litros <= 0:
            raise ValueError("Los litros deben ser mayores a 0")

        if precio <= 0:
            raise ValueError("El precio debe ser mayor a 0")

        total = litros * precio

        # -------------------------
        # CAMPOS EXTRA
        # -------------------------
        tipo_combustible = request.POST.get("tipo_combustible")
        if not tipo_combustible:
            raise ValueError("Selecciona tipo de combustible")

        observaciones = request.POST.get("observaciones")
        gasolinera = request.POST.get("gasolinera")

        odometro = request.POST.get("odometro")
        odometro = int(odometro) if odometro else None

        tanque_lleno = request.POST.get("tanque_lleno") == "on"

        foto = request.FILES.get("foto")

        # -------------------------
        # GUARDAR
        # -------------------------
        with transaction.atomic():

            carga = CargaCombustible.objects.create(
                equipo=equipo,
                fecha_carga=fecha_carga,
                folio=folio,
                cantidad_litros=litros,
                precio_litro=precio,
                costo_total=total,

                tipo_combustible=tipo_combustible,
                observaciones=observaciones,
                odometro=odometro,
                gasolinera=gasolinera,
                tanque_lleno=tanque_lleno,
                foto=foto,

                operador_fk=request.user,
                operador=request.user.get_full_name() or request.user.username,
                uc=request.user,
            )

        logger.info(f"Carga creada ID={carga.id} por {request.user}")

        # -------------------------
        # MENSAJE EXITO
        # -------------------------
        messages.success(
            request,
            f"✔ Carga registrada | Equipo: {carga.equipo} | Folio: {carga.folio} | Total: ${carga.costo_total}"
        )

        return redirect("adm:captura_combustible")

    except Exception as e:
        logger.error(f"Error captura combustible: {str(e)}")

        # -------------------------
        # MENSAJE ERROR
        # -------------------------
        messages.error(request, str(e))

        return redirect("adm:captura_combustible")
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
from adm.models import Equipo, CargaCombustible, ReporteEquipo, OrdenServicio



class Equipo360Service:
    @staticmethod
    def _to_decimal(valor):
        """
        Convierte valores como '8', '8.5', '08:30' o None a Decimal.
        Por ahora soporta texto simple y horas:minutos.
        """
        if valor is None:
            return Decimal("0")

        valor = str(valor).strip()

        if not valor:
            return Decimal("0")

        # Caso horas:minutos -> "08:30" => 8.50
        if ":" in valor:
            try:
                horas, minutos = valor.split(":")
                return Decimal(horas) + (Decimal(minutos) / Decimal("60"))
            except Exception:
                return Decimal("0")

        try:
            return Decimal(valor)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @classmethod
    def obtener_reporte_360(cls, equipo, fecha_inicio=None, fecha_fin=None):
        filtros_uso = {"equipo": equipo}
        filtros_combustible = {"equipo": equipo}
        filtros_servicio = {"equipo": equipo}

        if fecha_inicio and fecha_fin:
            filtros_uso["fecha__range"] = [fecha_inicio, fecha_fin]
            filtros_combustible["fecha_carga__range"] = [fecha_inicio, fecha_fin]
            filtros_servicio["fecha__range"] = [fecha_inicio, fecha_fin]

        # USO
        usos_qs = ReporteEquipo.objects.filter(**filtros_uso).order_by("-fecha")
        total_horas = Decimal("0")
        for uso in usos_qs:
            total_horas += cls._to_decimal(uso.horas)

        # COMBUSTIBLE
        combustible_qs = CargaCombustible.objects.filter(**filtros_combustible).order_by("-fecha_carga", "-id")
        total_litros = combustible_qs.aggregate(total=Sum("cantidad_litros"))["total"] or Decimal("0")
        total_costo_combustible = combustible_qs.aggregate(total=Sum("costo_total"))["total"] or Decimal("0")

        # SERVICIOS / MANTENIMIENTO
        servicios_qs = OrdenServicio.objects.filter(**filtros_servicio).order_by("-fecha", "-id")
        total_servicios = servicios_qs.count()
        servicios_abiertos = servicios_qs.filter(estatus__in=["ABIERTA", "AUTORIZADA", "PROCESO"]).count()
        servicios_cerrados = servicios_qs.filter(estatus="CERRADA").count()
        servicios_cancelados = servicios_qs.filter(estatus="CANCELADA").count()

        # INDICADORES
        litros_por_hora = Decimal("0")
        costo_combustible_por_hora = Decimal("0")

        if total_horas > 0:
            litros_por_hora = total_litros / total_horas
            costo_combustible_por_hora = total_costo_combustible / total_horas

        return {
            "equipo": equipo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,

            "usos_qs": usos_qs[:20],
            "combustible_qs": combustible_qs[:20],
            "servicios_qs": servicios_qs[:20],

            "total_horas": total_horas,
            "total_litros": total_litros,
            "total_costo_combustible": total_costo_combustible,
            "litros_por_hora": litros_por_hora,
            "costo_combustible_por_hora": costo_combustible_por_hora,

            "total_servicios": total_servicios,
            "servicios_abiertos": servicios_abiertos,
            "servicios_cerrados": servicios_cerrados,
            "servicios_cancelados": servicios_cancelados,
        }
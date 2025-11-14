from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from django.core.cache import cache
from nomina.models import (
    PeriodosNomina,
    NominaHistorial,
    NominaEmpleado,
    NominaDetalle,
    MovimientoCuentaProyecto,
    NominaAcumulado,
    Empleado, AsignacionDiaria
)
from adm.models import Proyecto
from django.db.models import F


from decimal import Decimal
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from nomina.models import (
    Empleado, NominaHistorial, NominaEmpleado, NominaDetalle,
    MovimientoCuentaProyecto
)

from adm.models import Proyecto


import json
from pathlib import Path



@transaction.atomic
def confirmar_nomina_desde_pdf(request):
    """
    Procesa la nómina confirmando los datos calculados desde el HTML.
    Crea los registros en NominaEmpleado, NominaDetalle, MovimientoCuentaProyecto
    y actualiza los acumulados mensuales/anuales considerando:
    - Cruce de meses.
    - Sueldo diario histórico.
    - Horas extras.
    """

    print("DEBUG >> Entrando a confirmar_nomina_desde_pdf()")

    base_dir = Path(__file__).resolve().parent.parent
    tmp_path = base_dir / "tmp_nomina_data.json"

    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            nomina_data = json.load(f)
        print(f"DEBUG >> Archivo leído correctamente con {len(nomina_data)} registros.")
    except FileNotFoundError:
        messages.error(request, "⚠️ No existe el archivo temporal de nómina. Calcula la nómina primero.")
        return False, None
    except Exception as e:
        print(f"❌ Error leyendo archivo: {e}")
        return False, None

    periodo_id = request.session.get("periodo_id")
    if not periodo_id:
        messages.error(request, "❌ No se ha seleccionado un período de nómina.")
        return False, None

    try:
        periodo = PeriodosNomina.objects.get(id=periodo_id)
    except PeriodosNomina.DoesNotExist:
        messages.error(request, "❌ El período de nómina no existe.")
        return False, None

    # Crear o recuperar historial
    historial, _ = NominaHistorial.objects.get_or_create(
        periodo_inicio=periodo.periodo_inicio,
        periodo_fin=periodo.periodo_final,
        defaults={"total_pago": Decimal("0.00"), "estatus": "Pendiente"},
    )

    # Limpieza previa
    NominaEmpleado.objects.filter(historial=historial).delete()
    MovimientoCuentaProyecto.objects.filter(periodo=historial).delete()

    total_general = Decimal("0.00")
    total_pdf = Decimal("0.00")

    print("\n=== 🔍 INICIO DE VERIFICACIÓN DE REGISTROS ===")

    # === Procesar cada empleado ===
    for reg in nomina_data:
        empleado_id = reg.get("empleado_id")
        if not empleado_id:
            continue

        try:
            empleado = Empleado.objects.get(pk=empleado_id)
        except Empleado.DoesNotExist:
            print(f"⚠️ Empleado con ID {empleado_id} no existe.")
            continue

        total_neto = Decimal(reg.get("total_pago", 0)).quantize(Decimal("0.01"))
        total_pdf += total_neto
        sueldo_diario = Decimal(reg.get("sueldo_diario", 0))
        horas_extras = Decimal(reg.get("horas_extras", 0))
        total_general += total_neto

        # === DEPURACIÓN INDIVIDUAL ===
        print(f"Empleado: {empleado.nombre} | Neto: {total_neto:,.2f} | "
              f"Sueldo diario: {sueldo_diario:,.2f} | Horas extra: {horas_extras:,.2f}")

        asignacion = (
            AsignacionDiaria.objects
            .filter(empleado=empleado, fecha__range=(periodo.periodo_inicio, periodo.periodo_final))
            .select_related("proyecto__cuenta")
            .first()
        )

        if not asignacion:
            print(f"⚠️ {empleado.nombre} sin proyecto asignado en este periodo.")
            continue

        proyecto = asignacion.proyecto
        cuenta = proyecto.cuenta

        # === Movimiento de cuenta ===
        if cuenta:
            cuenta.saldo_actual -= total_neto
            cuenta.save()
        else:
            print(f"⚠️ {empleado.nombre} no tiene cuenta asignada en el proyecto {proyecto.nombre}.")

        MovimientoCuentaProyecto.objects.create(
            proyecto=proyecto,
            empleado=empleado,
            periodo=historial,
            importe=total_neto,
        )

        # === Nómina del empleado ===
        nom_emp = NominaEmpleado.objects.create(
            historial=historial,
            empleado=empleado,
            proyecto=proyecto,
            total_percepciones=Decimal(reg.get("total_percepciones", 0)),
            total_deducciones=Decimal(reg.get("total_deducciones", 0)),
            total_neto=total_neto,
            dias_trabajados=Decimal(reg.get("dias_trabajados", 0)),
        )

        # === Detalle de percepciones ===
                # === Detalle de percepciones ===
        detalles = [
            NominaDetalle(
                nomina_empleado=nom_emp,
                concepto="Sueldo base trabajado",
                tipo="PERCEPCION",
                cantidad=1,
                monto_unitario=Decimal(reg.get("sueldo_semanal", 0)),
                subtotal=Decimal(reg.get("sueldo_semanal", 0)),
            ),
            NominaDetalle(
                nomina_empleado=nom_emp,
                concepto="Séptimo día",
                tipo="PERCEPCION",
                cantidad=1,
                monto_unitario=Decimal(reg.get("septimo_dia", 0)),
                subtotal=Decimal(reg.get("septimo_dia", 0)),
            ),
        ]

        # 👉 Agrega este bloque:
        if Decimal(reg.get("horas_extras", 0)) > 0:
            detalles.append(
                NominaDetalle(
                    nomina_empleado=nom_emp,
                    concepto="Horas extras",
                    tipo="PERCEPCION",
                    cantidad=1,
                    monto_unitario=Decimal(reg.get("horas_extras", 0)),
                    subtotal=Decimal(reg.get("horas_extras", 0)),
                )
            )

        NominaDetalle.objects.bulk_create(detalles)

        # === Manejo del cruce de mes ===
        try:
            mes_inicio = periodo.periodo_inicio.month
            mes_fin = periodo.periodo_final.month
            anio_inicio = periodo.periodo_inicio.year
            anio_fin = periodo.periodo_final.year

            asignaciones = AsignacionDiaria.objects.filter(
                empleado=empleado,
                fecha__range=(periodo.periodo_inicio, periodo.periodo_final)
            )

            dias_mes_inicio = asignaciones.filter(fecha__month=mes_inicio).count()
            dias_mes_fin = asignaciones.filter(fecha__month=mes_fin).count()
            total_dias_periodo = dias_mes_inicio + dias_mes_fin or 1

            factor_inicio = Decimal(dias_mes_inicio) / Decimal(total_dias_periodo)
            factor_fin = Decimal(dias_mes_fin) / Decimal(total_dias_periodo)

            importe_inicio = (total_neto * factor_inicio).quantize(Decimal("0.01"))
            importe_fin = (total_neto * factor_fin).quantize(Decimal("0.01"))

            # --- Acumulado del primer mes ---
            if dias_mes_inicio:
                acum1, created = NominaAcumulado.objects.get_or_create(
                    empleado=empleado,
                    mes=mes_inicio,
                    anio=anio_inicio,
                    proyecto=proyecto,
                    periodo=periodo,
                    defaults={
                        "dias_trabajados": dias_mes_inicio,
                        "importe": importe_inicio,
                        "sueldo_diario": sueldo_diario,
                        "horas_extras": horas_extras,
                    },
                )
                if not created:
                    acum1.dias_trabajados += dias_mes_inicio
                    acum1.importe += importe_inicio
                    acum1.sueldo_diario = sueldo_diario
                    acum1.horas_extras += horas_extras
                    acum1.save()

            # --- Acumulado del segundo mes (si cruza mes) ---
            if mes_fin != mes_inicio and dias_mes_fin:
                acum2, created = NominaAcumulado.objects.get_or_create(
                    empleado=empleado,
                    mes=mes_fin,
                    anio=anio_fin,
                    proyecto=proyecto,
                    periodo=periodo,
                    defaults={
                        "dias_trabajados": dias_mes_fin,
                        "importe": importe_fin,
                        "sueldo_diario": sueldo_diario,
                        "horas_extras": horas_extras,
                    },
                )
                if not created:
                    acum2.dias_trabajados += dias_mes_fin
                    acum2.importe += importe_fin
                    acum2.sueldo_diario = sueldo_diario
                    acum2.horas_extras += horas_extras
                    acum2.save()

        except Exception as e:
            print(f"⚠️ Error al actualizar acumulados mensuales: {e}")

    # === Cerrar historial ===
    historial.total_pago = total_general
    historial.estatus = "Procesada"
    historial.fecha_procesada = timezone.now()
    historial.save()

    # === Acumulados anuales ===
    actualizar_acumulados(historial)

    print("\n=== 🔍 VERIFICACIÓN FINAL ===")
    print(f"Total calculado desde JSON (PDF): ${total_pdf:,.2f}")
    print(f"Total registrado en BD:           ${total_general:,.2f}")
    diferencia = total_pdf - total_general
    print(f"⚠️ DIFERENCIA DETECTADA: {diferencia:,.2f} (si es distinta de 0, hay error en algún registro)")
    print("=============================================\n")

    messages.success(request, f"✅ Nómina procesada correctamente con total ${total_general:,.2f}")
    print(f"✅ Nómina final registrada: ${total_general:,.2f}")

    return True, historial.id
#========================================================================0
#
#========================================================================0






@transaction.atomic
def actualizar_acumulados(historial):
    """
    Actualiza los acumulados mensuales de nómina por empleado y proyecto.
    Si el periodo cruza meses, divide proporcionalmente el total según los días de cada mes.
    """

    # Buscar el PeriodosNomina real asociado al historial
    periodo_nomina = PeriodosNomina.objects.filter(
    periodo_inicio=historial.periodo_inicio,
    periodo_final=historial.periodo_fin
    ).first()


    if not periodo_nomina:
        print("⚠️ No se encontró PeriodosNomina asociado al historial, creando temporal.")
        periodo_nomina = PeriodosNomina.objects.create(
            periodo_inicio=historial.periodo_inicio,
            periodo_final=historial.periodo_fin,
            estatus='CERRADO'
        )


    # Extraer fechas del periodo correcto
    fecha_inicio = periodo_nomina.periodo_inicio
    fecha_fin = periodo_nomina.periodo_final

    print(f"🧾 Actualizando acumulados del {fecha_inicio} al {fecha_fin}")

    # Recorremos todos los empleados del historial
    for nomina_emp in historial.empleados.select_related('empleado').all():
        empleado = nomina_emp.empleado
        total_neto = nomina_emp.total_neto or Decimal("0.00")
        dias_trabajados = nomina_emp.dias_trabajados or Decimal("0.00")
        sueldo_diario = empleado.sueldo_diario or Decimal("0.00")
        horas_extras = Decimal("0.00")
        compensacion = Decimal("0.00")
        destajo = Decimal("0.00")

        # Buscar el proyecto del empleado en el periodo
        asignacion = (
            empleado.asignaciondiaria_set
            .filter(fecha__range=(fecha_inicio, fecha_fin))
            .select_related("proyecto")
            .first()
        )
        proyecto = asignacion.proyecto if asignacion else None

        # === Verificar cruce de mes ===
        if fecha_inicio.month == fecha_fin.month:
            # Todo el periodo dentro del mismo mes
            mes = fecha_inicio.month
            anio = fecha_inicio.year

            acum, _ = NominaAcumulado.objects.get_or_create(
                empleado=empleado,
                proyecto=proyecto,
                periodo=periodo_nomina,
                mes=mes,
                anio=anio,
                defaults={
                    'dias_trabajados': 0,
                    'sueldo_diario': sueldo_diario,
                    'horas_extras': 0,
                    'compensacion': 0,
                    'destajo': 0,
                    'importe': 0,
                }
            )

            acum.dias_trabajados += dias_trabajados
            acum.sueldo_diario = sueldo_diario
            acum.importe += total_neto
            acum.save()

        else:
            # Periodo cruza meses
            primer_mes = fecha_inicio.month
            segundo_mes = fecha_fin.month
            anio_1 = fecha_inicio.year
            anio_2 = fecha_fin.year

            # Calcular días del primer y segundo mes
            dias_total = (fecha_fin - fecha_inicio).days + 1
            fin_mes1 = (fecha_inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
            dias_mes1 = (fin_mes1 - fecha_inicio).days
            dias_mes1 = min(dias_mes1, dias_total)
            dias_mes2 = dias_total - dias_mes1

            # Proporción del total neto por mes
            proporcion_mes1 = (Decimal(dias_mes1) / Decimal(dias_total)) * total_neto
            proporcion_mes2 = (Decimal(dias_mes2) / Decimal(dias_total)) * total_neto

            # Acumulado primer mes
            acum1, _ = NominaAcumulado.objects.get_or_create(
                empleado=empleado,
                proyecto=proyecto,
                periodo=periodo_nomina,
                mes=primer_mes,
                anio=anio_1,
                defaults={
                    'dias_trabajados': 0,
                    'sueldo_diario': sueldo_diario,
                    'horas_extras': 0,
                    'compensacion': 0,
                    'destajo': 0,
                    'importe': 0,
                }
            )
            acum1.dias_trabajados += Decimal(dias_mes1)
            acum1.importe += proporcion_mes1.quantize(Decimal("0.01"))
            acum1.save()

            # Acumulado segundo mes
            acum2, _ = NominaAcumulado.objects.get_or_create(
                empleado=empleado,
                proyecto=proyecto,
                periodo=periodo_nomina,
                mes=segundo_mes,
                anio=anio_2,
                defaults={
                    'dias_trabajados': 0,
                    'sueldo_diario': sueldo_diario,
                    'horas_extras': 0,
                    'compensacion': 0,
                    'destajo': 0,
                    'importe': 0,
                }
            )
            acum2.dias_trabajados += Decimal(dias_mes2)
            acum2.importe += proporcion_mes2.quantize(Decimal("0.01"))
            acum2.save()

    print("✅ Acumulados actualizados correctamente.")

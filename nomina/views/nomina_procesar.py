# nomina/views/nomina_procesar.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from nomina.models import (NominaHistorial, NominaDetalle, NominaEmpleado,
    PeriodosNomina,  AsignacionDiaria, MovimientoCuentaProyecto)
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal

#=================================================================
# 
# Inicio de procesa nomina
# 
#=================================================================






from nomina.views.nomina_procesar_utils import (
    poblar_base_desde_asignaciones,
    poblar_horas_extras,
    poblar_compensacion_variable,
    recalcular_totales_nomina,
)



# @transaction.atomic
# def procesar_nomina(request):
#     try:
#         periodo_id = request.session.get("periodo_id")
#         if not periodo_id:
#             messages.error(request, "⚠️ No se ha seleccionado un período de nómina.")
#             return redirect("nom:calcular_nomina")

#         periodo = PeriodosNomina.objects.get(id=periodo_id)

#         # Crear o recuperar el historial del período
#         nomina_historial, _ = NominaHistorial.objects.get_or_create(
#             periodo_inicio=periodo.periodo_inicio,
#             periodo_fin=periodo.periodo_final,
#             defaults={"total_pago": 0}
#         )

#         # ===================================================
#         # Procesamiento secuencial
#         # ===================================================
#         poblar_base_desde_asignaciones(nomina_historial)
#         poblar_horas_extras(nomina_historial)
#         poblar_compensacion_variable(nomina_historial)
#         recalcular_totales_nomina(nomina_historial)

#         nomina_historial.estatus = "Procesada"
#         nomina_historial.save()

#         messages.success(request, f"✅ Nómina procesada correctamente ({periodo})")
#         return redirect("nom:nomina_detalle", pk=nomina_historial.id)

#     except PeriodosNomina.DoesNotExist:
#         messages.error(request, "⚠️ El período de nómina seleccionado no existe.")
#         return redirect("nom:calcular_nomina")

#     except Exception as e:
#         messages.error(request, f"❌ Ocurrió un error al procesar la nómina: {e}")
#         return redirect("nom:calcular_nomina")
#=================================================================
# 
# fin de procesa nomina
# 
#=================================================================
    


def procesar_nomina_form(request):
    periodo_id = request.session.get('periodo_id')
    periodo_semana = request.session.get('periodo_semana')
    fecha_inicio = request.session.get('periodo_inicio')
    fecha_fin = request.session.get('periodo_final')

    if not periodo_id:
        messages.error(request, "Primero seleccione un período.")
        return redirect('nom:seleccionar_fecha')

    context = {
        'periodo_id': periodo_id,
        'semana': periodo_semana,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    return render(request, 'nomina/procesar_nomina.html', context)




from django.contrib import messages
from django.shortcuts import redirect
from nomina.views.nomina_confirmar_utils import confirmar_nomina_desde_pdf

def procesar_nomina(request):
    print("DEBUG >> Entrando a procesar_nomina()")
    ok, historial_id = confirmar_nomina_desde_pdf(request)
    print("DEBUG >> Resultado confirmar_nomina_desde_pdf:", ok, historial_id)

    if ok and historial_id:
        messages.success(request, "✅ Nómina procesada correctamente.")
        return redirect("nom:nomina_detalle", pk=historial_id)
    else:
        messages.warning(request, "⚠️ No se procesó la nómina (revisa logs).")
        return redirect("nom:calcular_nomina")

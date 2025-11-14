# nomina/views/nomina_procesar.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from nomina.models import (NominaHistorial, 
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, NominaEmpleado, NominaAcumulado)
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum
from django.utils.timezone import now
from django.db import transaction




@transaction.atomic
def cerrar_nomina(request, pk):
    """
    Cierra formalmente la nómina sin recalcular totales.
    Solo cambia el estatus y registra la fecha de cierre.
    """
    historial = get_object_or_404(NominaHistorial, pk=pk)

    # Validación del estatus actual
    if historial.estatus not in ["Procesada", "PROCESADA"]:
        messages.warning(request, f"⚠️ La nómina ya está cerrada o cancelada.")
        return redirect("nom:nomina_detalle", pk=pk)

    # Marcar cierre
    historial.estatus = "CERRADA"
    historial.fecha_cierre = timezone.now()
    historial.save()

    # 🔹 Actualizar también el estatus del período asociado
    from nomina.models import PeriodosNomina

    try:
        periodo = PeriodosNomina.objects.get(
            periodo_inicio=historial.periodo_inicio,
            periodo_final=historial.periodo_fin
        )
        periodo.estatus = "CERRADO"
        periodo.save()
        print(f"🗓️ Periodo {periodo.id} cerrado correctamente.")
    except PeriodosNomina.DoesNotExist:
        print("⚠️ No se encontró el periodo asociado para cerrar.")


    messages.success(
        request,
        f"✅ Nómina cerrada correctamente. Total aplicado: ${historial.total_pago:,.2f}"
    )
    print(f"🧾 Nómina {historial.id} cerrada con total aplicado ${historial.total_pago:,.2f}")
    return redirect("nom:nomina_detalle", pk=pk)


@login_required(login_url='bases:login')
def nominas_cerradas_list(request):
    
    
    # Filtramos las nóminas que tienen el estatus 'Cerrada'
    # Asumiendo que tu campo de estatus en NominaHistorial se llama 'estatus'
    # y el valor para 'Cerrada' es 'Cerrada'.
    nominas_cerradas = NominaHistorial.objects.filter(estatus='CERRADA').order_by('-fecha_procesada')
    
    context = {
        'nominas_cerradas': nominas_cerradas,
        'titulo': 'Nóminas Cerradas', # Un título útil para la plantilla
    }
    
    
    return render(request, 'nomina/nominas_cerradas_list.html', context)



@transaction.atomic
def actualizar_acumulados(historial):
    nominas = NominaEmpleado.objects.filter(historial=historial)
    for n in nominas:
        anio = historial.periodo_nomina.anio
        mes = historial.periodo_nomina.periodo_inicio.month
        acum, _ = NominaAcumulado.objects.get_or_create(
            empleado=n.empleado,
            proyecto=n.proyecto,
            anio=anio,
            mes=mes,
            defaults={'percepciones': 0, 'deducciones': 0, 'neto': 0}
        )
        acum.percepciones += n.total_percepciones
        acum.deducciones += n.total_deducciones
        acum.neto += n.total_neto
        acum.save()



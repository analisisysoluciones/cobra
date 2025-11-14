# nomina/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.views import generic
from django.views import View
from django.http import JsonResponse, HttpResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from nomina.models import (
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, TipoDestajo, TarifaDiariaObra, TarifaDestajoObra,
    RegistroDestajo
    )
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from nomina.forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaEmpleadoProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, TipoDestajoForm
)
from xhtml2pdf import pisa
from django.template.loader import render_to_string, get_template
from django.contrib import messages
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Max, Q, Count, F, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from decimal import Decimal
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader


def asignar_proyectos(request, nomina_id):
    print(f"DEBUG: *** Entrando a asignar_proyectos para nomina ID: {nomina_id} ***")
    
    nomina = get_object_or_404(NominaHistorial, id=nomina_id)
    print(f"DEBUG: Nómina Historial obtenida: {nomina.id}, Periodo: {nomina.periodo_inicio} - {nomina.periodo_fin}")
    
    detalles = NominaDetalle.objects.filter(nomina_historica=nomina).select_related('empleado', 'proyecto')
    print(f"DEBUG: Detalles de nómina encontrados: {detalles.count()}")
    
    # Imprime un detalle para verificar sus propiedades
    if detalles.exists():
        first_detalle = detalles.first()
        print(f"DEBUG: Primer detalle - ID: {first_detalle.id}, Empleado: {first_detalle.empleado.nombre}, Proyecto actual: {first_detalle.proyecto}")
    else:
        print("DEBUG: No se encontraron detalles de nómina para esta nómina.")

    proyectos = Proyecto.objects.all().order_by('nombre')
    print(f"DEBUG: Proyectos disponibles: {proyectos.count()}")

    if request.method == "POST":
        print("DEBUG: Procesando POST para asignación de proyectos...")
        updated_count = 0
        errors_count = 0
        try:
            with transaction.atomic():
                for key, value in request.POST.items():
                    if key.startswith("proyecto_"):
                        try:
                            detalle_id = int(key.split("_")[1])
                            proyecto_id = int(value)
                            detalle = NominaDetalle.objects.get(id=detalle_id, nomina_historica=nomina)
                            
                            if proyecto_id == 0 or value == '': # Asume 0 o cadena vacía para desasignar
                                detalle.proyecto = None
                            else:
                                proyecto = Proyecto.objects.get(id=proyecto_id)
                                detalle.proyecto = proyecto
                            
                            detalle.save()
                            updated_count += 1
                        except (NominaDetalle.DoesNotExist, Proyecto.DoesNotExist, ValueError) as e:
                            errors_count += 1
                            print(f"DEBUG: ERROR al asignar proyecto al detalle {detalle_id}: {e}")
                            messages.warning(request, f"No se pudo asignar proyecto al detalle ID {detalle_id}: {e}") # Mostrar errores individuales
                            continue 
                if updated_count > 0:
                    messages.success(request, f"Se asignaron proyectos a {updated_count} detalles de nómina.")
                if errors_count > 0:
                    messages.warning(request, f"Hubo {errors_count} errores al intentar asignar proyectos. Revisa los detalles.")
                
                print(f"DEBUG: Redirigiendo a nom:asignar_proyectos con nomina_id={nomina.id}")
                return redirect('nom:asignar_proyectos', nomina_id=nomina.id)
        except Exception as e:
            messages.error(request, f"Ocurrió un error inesperado al guardar las asignaciones: {e}")
            print(f"DEBUG: ERROR General en POST de asignar_proyectos: {e}")
            return redirect('nom:asignar_proyectos', nomina_id=nomina.id)

    print("DEBUG: Renderizando template nomina/asignar_proyectos.html")
    #return render(request, 'nomina/asignar_proyectos.html', {
    return render(request, 'nomina/nomina_detalle.html', {
        'nomina': nomina,
        'detalles': detalles,
        'proyectos': proyectos,
    })


class NominaDetalleListView(generic.ListView):
    model = NominaDetalle
    template_name = 'nomina/asignar_proyectos.html'
    context_object_name = 'detalles'

    def get_queryset(self):
        return NominaDetalle.objects.filter(nomina_historica_id=self.kwargs['nomina_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nomina_id'] = self.kwargs['nomina_id']
        return context


class NominaDetalleUpdateView(generic.UpdateView):
    model = NominaDetalle
    form_class = NominaEmpleadoProyectoForm
    template_name = 'nomina/editar_proyecto.html'

    def get_success_url(self):
        return reverse_lazy('nom:asignar_proyecto', kwargs={
            'nomina_id': self.object.nomina_historica_id
        })


class NominaDetalleUpdateView(generic.UpdateView):
    # ... tu código actual ...
    def get_success_url(self):
        nomina_historial_id = self.object.nomina_historica.id 
        messages.success(self.request, "Proyecto asignado correctamente.")
        print(f"DEBUG: Redirigiendo desde NominaDetalleUpdateView a nom:asignar_proyectos con nomina_id={nomina_historial_id}")
        return reverse_lazy('nom:asignar_proyectos', kwargs={'nomina_id': nomina_historial_id})


@login_required(login_url='bases:login')
def asignar_proyecto_individual(request, detalle_id):
    detalle = get_object_or_404(NominaDetalle, id=detalle_id)

    if not detalle.nomina_historica:
        messages.error(request, "El detalle de nómina no está asociado a un historial válido.")
        return redirect('nom:seleccionar_fecha')

    nomina_historial_id = detalle.nomina_historica.id

    if request.method == "POST":
        form = AsignarProyectoForm(request.POST, instance=detalle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Proyecto asignado a {detalle.empleado.nombre} correctamente.")
            return redirect('nom:listar_detalles_nomina_procesada', nomina_historial_id=nomina_historial_id)
        else:
            messages.error(request, "Error al asignar el proyecto. Verifique los datos.")
    else:
        form = AsignarProyectoForm(instance=detalle)

    context = {
        'form': form,
        'detalle': detalle,
        'nomina_historial_id': nomina_historial_id,
    }
    return render(request, 'nomina/asignar_proyecto.html', context)

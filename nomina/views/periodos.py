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



class PeriodosNominaList(LoginRequiredMixin, generic.ListView):
    model = PeriodosNomina
    template_name = "nomina/periodos_list.html"
    context_object_name = "periodos"
    login_url = 'bases:login'

class PeriodosNominaNew(LoginRequiredMixin, generic.CreateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('nom:periodos_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)

class PeriodosNominaEdit(LoginRequiredMixin, generic.UpdateView):
    model = PeriodosNomina
    form_class = PeriodosNominaForm
    template_name = 'nomina/periodos_nomina_form.html'
    success_url = reverse_lazy('nom:periodos_list')
    login_url = 'bases:login'

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class PeriodosNominaDel(LoginRequiredMixin, generic.DeleteView):
    model = PeriodosNomina
    template_name = "nomina/periodos_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:periodos_list")
    login_url = "bases:login"


def seleccionar_periodo(request):
    # Solo mostrar periodos activos (Abierto o En Proceso)
    periodos = PeriodosNomina.objects.filter(
        estatus__in=['ABIERTO', 'EN PROCESO']
    ).order_by('-periodo_inicio')

    periodo_id = request.session.get('periodo_id')

    print(f"TOTAL PERIODOS DISPONIBLES: {periodos.count()}")
    return render(request, 'nomina/periodo_semanal.html', {
        'periodos': periodos,
        'periodo_id': periodo_id,
    })


def seleccionar_periodo_nomina(request):
    print("🔍 DEBUG: Entrando a seleccionar_periodo_nomina")
    print(f"🔍 DEBUG: Método: {request.method}")

    if request.method == 'POST':
        print("🔍 DEBUG: Es POST")
        form = SeleccionarPeriodoForm(request.POST, request=request)

        print(f"🔍 DEBUG: Form data: {request.POST}")

        if form.is_valid():
            periodo = form.cleaned_data['periodo']
            print(f"🔍 DEBUG: Periodo seleccionado: {periodo}")

            # Validar estatus del periodo antes de continuar
            if periodo.estatus in ['CERRADO', 'CANCELADO']:
                messages.error(request, f"⚠️ El período '{periodo}' ya está {periodo.estatus.lower()}.")
                return redirect('nom:seleccionar_fecha')

            # Guardar datos en sesión
            request.session['periodo_id'] = periodo.id
            request.session['periodo_semana'] = periodo.semana
            request.session['periodo_inicio'] = str(periodo.periodo_inicio)
            request.session['periodo_final'] = str(periodo.periodo_final)

            print(f"🔍 DEBUG: Datos guardados en session: {request.session.get('periodo_id')}")
            print("🔍 DEBUG: Haciendo redirect a nom:calcular_nomina")
            request.session.modified = True


            return redirect('nom:calcular_nomina')
        else:
            print(f"🔍 DEBUG: Form NO es válido. Errores: {form.errors}")
    else:
        print("🔍 DEBUG: Es GET, creando form vacío")
        form = SeleccionarPeriodoForm(request=request)


    print("🔍 DEBUG: Renderizando template seleccionar_fecha.html")
    return render(request, 'nomina/seleccionar_fecha.html', {'form': form})

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


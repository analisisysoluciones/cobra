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


@login_required(login_url='bases:login')
def capturar_falta(request):
    if request.method == 'POST':
        form = FaltaForm(request.POST)
        if form.is_valid():
            asistencia = form.save(commit=False)
            asistencia.tipo = 'F'
            asistencia.save()
            messages.success(request, 'Falta registrada exitosamente.')
            return redirect('nom:capturar_falta')
        else:
            messages.error(request, 'Error al registrar la falta. Verifique los datos.')
    else:
        form = FaltaForm()
    return render(request, 'nomina/capturar_falta.html', {'form': form})


class AsistenciaListView(LoginRequiredMixin, generic.ListView):
    model = Asistencia
    template_name = "nomina/asistencia_list.html"
    context_object_name = "obj"
    login_url = 'bases:login'

class AsistenciaDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Asistencia
    template_name = "nomina/asistencia_confirm_delete.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:asistencia_list")
    login_url = "bases:login"


class CapturarFaltaModalView(generic.CreateView):
    model = Asistencia
    form_class = FaltaForm
    template_name = "nomina/falta_modal_form.html"

    def get(self, request, *args, **kwargs):
        empleado = get_object_or_404(Empleado, pk=kwargs.get("empleado_id"))
        form = self.form_class(initial={"empleado": empleado})
        html_form = render_to_string(self.template_name, {"form": form, "empleado": empleado}, request=request)
        return JsonResponse({"html_form": html_form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})
        return JsonResponse({
            "success": False,
            "html_form": render_to_string(self.template_name, {"form": form}, request=request)
        })

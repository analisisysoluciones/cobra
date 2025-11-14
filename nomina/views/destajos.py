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
    NominaEmpleadoProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, 
    TipoDestajoForm
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





# ----------- CATÁLOGO DE TIPO DE DESTAJO -----------
class TipoDestajoListView(LoginRequiredMixin, generic.ListView):
    model = TipoDestajo
    template_name = "nomina/tipo_destajo_list.html"
    context_object_name = "destajos"


class TipoDestajoCreateView(LoginRequiredMixin, generic.CreateView):
    model = TipoDestajo
    form_class = TipoDestajoForm
    template_name = "nomina/tipo_destajo_form.html"
    success_url = reverse_lazy("tipo_destajo_list") 


class TipoDestajoUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = TipoDestajo
    form_class = TipoDestajoForm
    template_name = "nomina/tipo_destajo_form.html"
    success_url = reverse_lazy("tipo_destajo_list")


class TipoDestajoDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = TipoDestajo
    template_name = "nomina/tipo_destajo_confirm_delete.html"
    success_url = reverse_lazy("tipo_destajo_list")


# ----------- TARIFA POR OBRA -----------
class TarifaDestajoObraListView(LoginRequiredMixin, generic.ListView):
    model = TarifaDestajoObra
    template_name = "nomina/tarifa_destajo_obra_list.html"
    context_object_name = "tarifas"
    queryset = TarifaDestajoObra.objects.select_related("obra", "tipo")


class TarifaDestajoObraCreateView(LoginRequiredMixin, generic.CreateView):
    model = TarifaDestajoObra
    form_class = TarifaDestajoObraForm
    template_name = "nomina/tarifa_destajo_obra_form.html"
    success_url = reverse_lazy("tarifa_destajo_obra_list")


class TarifaDestajoObraUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = TarifaDestajoObra
    form_class = TarifaDestajoObraForm
    template_name = "nomina/tarifa_destajo_obra_form.html"
    success_url = reverse_lazy("tarifa_destajo_obra_list")


class TarifaDestajoObraDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = TarifaDestajoObra
    template_name = "nomina/tarifa_destajo_obra_confirm_delete.html"
    success_url = reverse_lazy("tarifa_destajo_obra_list")

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.views import generic,View
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

# --- Vistas existentes y corregidas ---

class EmpleadoList(LoginRequiredMixin, generic.ListView):
    model = Empleado
    template_name = "nomina/empleado_list.html"
    context_object_name = "empleados"
    login_url = 'bases:login'
    ordering = ['codigo']
    
    

    

class EmpleadoNew(LoginRequiredMixin, generic.CreateView):
    model = Empleado
    template_name = "nomina/empleado_form.html"
    context_object_name = "obj"
    form_class = EmpleadoForm
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)
    

class EmpleadoEdit(LoginRequiredMixin, generic.UpdateView):
    model = Empleado
    template_name = "nomina/empleado_form.html"
    form_class = EmpleadoForm
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class EmpleadoDel(LoginRequiredMixin, generic.DeleteView):
    model = Empleado
    template_name = "nomina/empleado_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("nom:empleado_list")
    login_url = "bases:login"

@login_required(login_url='bases:login')
def DocumentoEmpleadoDelete(request, pk):
    doc = get_object_or_404(EmpleadoArchivo, pk=pk)
    empleado_pk = doc.empleado.pk
    doc.delete()
    messages.success(request, f"Documento eliminado correctamente.")
    return redirect('nom:empleado_edit', pk=empleado_pk)


@login_required(login_url='bases:login')
def validar_curp(request):
    curp = request.GET.get('curp', None)
    data = {
        'is_taken': Empleado.objects.filter(curp__iexact=curp).exists()
    }
    return JsonResponse(data)


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
from .models import (
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, TipoDestajo, TarifaDiariaObra, TarifaDestajoObra,
    RegistroDestajo
    )
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from .forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaDetalleProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, TipoDestajoForm
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



logger = logging.getLogger(__name__)







# --- Funciones para PDF ---









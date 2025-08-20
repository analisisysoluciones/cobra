# nomina/forms.py
from django import forms
import datetime
from django.core.exceptions import ValidationError
from adm.models import Proyecto # <-- CORREGIDO: Importar Proyecto desde adm.models
from .models import (
    Cuenta, Empleado, Asistencia, Nomina, PeriodosNomina, EmpleadoArchivo, NominaDetalle, AsignacionDiaria
)
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.forms import inlineformset_factory, modelformset_factory, BaseModelFormSet
from django.urls import reverse_lazy


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ['codigo', 'curp', 'rfc', 'nombre', 'ingreso', 'sueldo_diario', 'compensacion', 'puesto', 'estado']
        widgets = {
            'codigo': forms.NumberInput(attrs={'class': 'form-control'}),
            'curp': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'text-transform:uppercase;',
                'data-url': reverse_lazy('nom:validar_curp')  # Ruta para AJAX
            }),
            'rfc': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform:uppercase;'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ingreso': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'sueldo_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'compensacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'puesto': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
        }

class EmpleadoArchivoForm(forms.ModelForm):
    class Meta:
        model = EmpleadoArchivo
        # Eliminado 'nombre_archivo' de aquí porque no existe en el modelo EmpleadoArchivo
        fields = ['archivo'] # <-- CORREGIDO
        widgets = {
            'archivo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

class FaltaForm(forms.ModelForm):
    class Meta:
        model = Asistencia
        fields = ['empleado', 'fecha']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control select2'}), # Usa select2 si lo tienes configurado
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }



class PeriodosNominaForm(forms.ModelForm):
    class Meta:
        model = PeriodosNomina
        fields = ['semana', 'periodo_inicio', 'periodo_final', 'fecha_corte', 'dia_pago']
        widgets = {
            'periodo_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'), # <-- Añadir format
            'periodo_final': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),   # <-- Añadir format
            'fecha_corte': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),     # <-- Añadir format
            'dia_pago': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),        # <-- Añadir format
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['periodo_inicio', 'periodo_final', 'fecha_corte', 'dia_pago']:
            # El input_formats debe incluir el formato que el widget va a producir y otros posibles de entrada
            self.fields[field_name].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']


class AsignarProyectoForm(forms.ModelForm):
    class Meta:
        model = NominaDetalle
        fields = ['proyecto'] # Solo necesitamos el campo 'proyecto'

        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegura que el queryset sea de todos los proyectos o filtra si es necesario
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---" # Opcional


class SeleccionarPeriodoForm(forms.Form):
    periodo = forms.ModelChoiceField(
        queryset=PeriodosNomina.objects.all().order_by('periodo_inicio'),
        widget=forms.Select(attrs={'class': 'form-control select2', 'style': 'width: 50%;'}),
        empty_label="--- Seleccione un Período de Nómina ---",
        label="Período de Nómina",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ProcesarNominaForm(forms.Form):
    periodo = forms.ModelChoiceField(
        queryset=PeriodosNomina.objects.all(),
        label="Período de Nómina",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    cuenta = forms.ModelChoiceField(
        queryset=Cuenta.objects.all(),
        label="Cuenta para Pago",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

class NominaDetalleProyectoForm(forms.ModelForm):
    class Meta:
        model = NominaDetalle
        fields = ['proyecto']
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control'}),



        }    


# ... (imports existentes)

class AsignacionDiariaForm(forms.ModelForm):
    class Meta:
        model = AsignacionDiaria
        fields = ['empleado', 'proyecto', 'fecha', 'horas_trabajadas']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_empleado', 'style': 'width: 100%;'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_proyecto', 'style': 'width: 100%;'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horas_trabajadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0', 'max': '12'}),
        }

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---"
        self.fields['empleado'].queryset = Empleado.objects.all()
        self.fields['empleado'].empty_label = "--- Seleccione un Empleado ---"

    
    def clean(self):
        cleaned_data = super().clean()
        # Validación en form: Reforzar si hay falta (redundante con model, pero para UX)
        empleado = cleaned_data.get('empleado')  # Asume que se pasa en init si es formset
        fecha = cleaned_data.get('fecha')
        if empleado and fecha and Asistencia.objects.filter(empleado=empleado, fecha=fecha).exists():
            raise ValidationError("No se puede asignar: Hay una falta registrada para este día.")
        return cleaned_data

# Formset para edición masiva
AsignacionDiariaFormSet = modelformset_factory(
    AsignacionDiaria,
    form=AsignacionDiariaForm,
    extra=5,  # No extras; genera basado en queryset en view
    can_delete=False  # Opcional: permite eliminar asignaciones
)
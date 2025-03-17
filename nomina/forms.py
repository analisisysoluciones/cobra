from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import( Cuenta, Empleado, Asistencia, Nomina, PeriodosNomina, EmpleadoArchivo)
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
                'data-url': reverse_lazy('validar_curp')  # Ruta para AJAX
            }),
            'rfc': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform:uppercase;'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ingreso': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'sueldo_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'compensacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'puesto': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def clean_curp(self):
        curp = self.cleaned_data.get('curp', '').upper()
        if Empleado.objects.filter(curp=curp).exists():
            raise forms.ValidationError("Este CURP ya está registrado.")
        return curp
    
    
class EmpleadoArchivoForm(forms.ModelForm):
    class Meta:
        model = EmpleadoArchivo
        fields = ['nombre', 'archivo']

    def clean_archivo(self):
        nombre = self.cleaned_data.get('nombre_archivo')
        archivo = self.cleaned_data.get('archivo')

        # Validar que el archivo sea PDF
        if archivo and not archivo.name.endswith('.pdf'):
            raise forms.ValidationError("Solo se permiten archivos en formato PDF.")

        return archivo




class FaltaForm(forms.ModelForm):
    class Meta:
        model = Asistencia
        fields = ['empleado', 'fecha'] # Solo necesitamos empleado y fecha
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),  # Widget para seleccionar la fecha
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.filter(estado=True)

class FechaForm(forms.Form):
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'id': 'id_fecha'
        }),
        label="Fecha"
    )


class PeriodosNominaForm(forms.ModelForm):
    class Meta:
        model = PeriodosNomina
        fields = ['semana', 'periodo_inicio', 'periodo_final', 'fecha_corte', 'dia_pago']
        widgets = {
            'periodo_inicio': forms.DateInput(attrs={'type': 'date'}),
            'periodo_final': forms.DateInput(attrs={'type': 'date'}),
            'fecha_corte': forms.DateInput(attrs={'type': 'date'}),
            'dia_pago': forms.DateInput(attrs={'type': 'date'}),
        }


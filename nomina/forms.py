# nomina/forms.py
from django import forms
import datetime
from django.core.exceptions import ValidationError
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
from django.db.models import Sum

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
        from adm.models import Proyecto
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


    
# class AsignacionDiariaForm(forms.ModelForm):
#     class Meta:
#         model = AsignacionDiaria
#         # Temporalmente excluimos 'proyecto' para evitar la carga automática
#         fields = ['empleado', 'fecha', 'horas_trabajadas']
#         widgets = {
#             'empleado': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_empleado', 'style': 'width: 100%;'}),
#             'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#             'horas_trabajadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0', 'max': '12'}),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Importar Proyecto dentro de __init__ para evitar circularidad
#         from adm.models import Proyecto
        
#         # Agregar manualmente el campo proyecto
#         self.fields['proyecto'] = forms.ModelChoiceField(
#             queryset=Proyecto.objects.all(),
#             widget=forms.Select(attrs={'class': 'form-control select2', 'id': 'id_proyecto', 'style': 'width: 100%;'}),
#             empty_label="--- Seleccione un Proyecto ---",
#             required=False  # Ajusta según tus necesidades
#         )
        
#         self.fields['empleado'].queryset = Empleado.objects.all()
#         self.fields['empleado'].empty_label = "--- Seleccione un Empleado ---"
        
#         # Reordenar los campos para que aparezcan en el orden deseado
#         field_order = ['empleado', 'proyecto', 'fecha', 'horas_trabajadas']
#         self.fields = {key: self.fields[key] for key in field_order if key in self.fields}

#     # ... resto de los métodos clean() igual
#     def clean(self):
#         cleaned_data = super().clean()
#         empleado = cleaned_data.get('empleado')
#         fecha = cleaned_data.get('fecha')
#         proyecto = cleaned_data.get('proyecto')
#         horas_trabajadas = cleaned_data.get('horas_trabajadas')

#         # Validar unicidad de empleado, fecha y proyecto
#         if empleado and fecha and proyecto is not None:
#             if AsignacionDiaria.objects.filter(
#                 empleado=empleado,
#                 fecha=fecha,
#                 proyecto=proyecto
#             ).exclude(pk=self.instance.pk).exists():
#                 raise forms.ValidationError(
#                     f"Ya existe una asignación para {empleado} en {fecha} con el proyecto {proyecto or 'Sin Proyecto'}."
#                 )

#         # Validar falta en Asistencia
#         if empleado and fecha and Asistencia.objects.filter(empleado=empleado, fecha=fecha).exists():
#             raise forms.ValidationError("No se puede asignar: Hay una falta registrada para este día.")

#         # Validar máximo 12 horas por día
#         if empleado and fecha and horas_trabajadas:
#             total_horas = AsignacionDiaria.objects.filter(
#                 empleado=empleado,
#                 fecha=fecha
#             ).exclude(pk=self.instance.pk).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
#             if total_horas + horas_trabajadas > 12:
#                 raise forms.ValidationError("El total de horas por día no puede exceder 12.")

#         return cleaned_data




class AsignacionDiariaForm(forms.ModelForm):
    class Meta:
        model = AsignacionDiaria
        fields = ['empleado', 'fecha', 'proyecto', 'horas_trabajadas']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_empleado', 'style': 'width: 100%;'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_proyecto', 'style': 'width: 100%;'}),
            'horas_trabajadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0', 'max': '12'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar querysets
        from adm.models import Proyecto
        self.fields['empleado'].queryset = Empleado.objects.all()
        self.fields['empleado'].empty_label = "--- Seleccione un Empleado ---"
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---"
        self.fields['proyecto'].required = False  # Coherente con null=True

        # Inicializar valores existentes
        if self.instance and self.instance.pk:
            if self.instance.empleado:
                self.fields['empleado'].initial = self.instance.empleado.pk
            if self.instance.proyecto:
                self.fields['proyecto'].initial = self.instance.proyecto.pk
            if self.instance.fecha:
                self.fields['fecha'].initial = self.instance.fecha  # YYYY-MM-DD automático

    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        fecha = cleaned_data.get('fecha')
        proyecto = cleaned_data.get('proyecto')
        horas_trabajadas = cleaned_data.get('horas_trabajadas')

        # Validar unicidad
        if empleado and fecha and proyecto is not None:
            if AsignacionDiaria.objects.filter(
                empleado=empleado,
                fecha=fecha,
                proyecto=proyecto
            ).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f"Ya existe una asignación para {empleado} en {fecha} con el proyecto {proyecto or 'Sin Proyecto'}."
                )

        # Validar falta en Asistencia
        if empleado and fecha and Asistencia.objects.filter(empleado=empleado, fecha=fecha).exists():
            raise forms.ValidationError("No se puede asignar: Hay una falta registrada para este día.")

        # Validar máximo 12 horas
        if empleado and fecha and horas_trabajadas:
            total_horas = AsignacionDiaria.objects.filter(
                empleado=empleado,
                fecha=fecha
            ).exclude(pk=self.instance.pk).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
            if total_horas + horas_trabajadas > 12:
                raise forms.ValidationError("El total de horas por día no puede exceder 12.")

        return cleaned_data
    

# Formset para edición masiva
AsignacionDiariaFormSet = modelformset_factory(
    AsignacionDiaria,
    form=AsignacionDiariaForm,
    extra=5,  # No extras; genera basado en queryset en view
    can_delete=False  # Opcional: permite eliminar asignaciones
)
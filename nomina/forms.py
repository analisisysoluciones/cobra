# nomina/forms.py
from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import (
    Cuenta, Empleado, Asistencia, Nomina, PeriodosNomina, EmpleadoArchivo, NominaDetalle, AsignacionDiaria, RegistraAsistencia,
    TarifaDestajoObra, TipoDestajo, HorasExtras, NominaEmpleado, CompensacionVariable
)
from adm.models import Proyecto
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
        fields = [
            'curp',
            'rfc',
            'nombre',
            'ingreso',
            'sueldo_diario',
            'compensacion',
            'perfil',
            'estado'
        ]
        widgets = {
            'curp': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'text-transform:uppercase;',
                'data-url': reverse_lazy('nom:validar_curp')
            }),
            'rfc': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform:uppercase;'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ingreso': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}),
            'sueldo_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'compensacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'perfil': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),  # ← ERROR CORREGIDO
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.fields['perfil'].queryset = PerfilPuesto.objects.filter(activo=True).order_by('nombre')

        def clean(self):
            cleaned_data = super().clean()

            perfil = cleaned_data.get('perfil')

            if perfil:
                # sueldo lo impone el perfil
                cleaned_data['sueldo_diario'] = perfil.sueldo_base
            return cleaned_data

        def form_valid(self, form):
            empleado = form.save(commit=False)

            empleado.tipo_pago = empleado.perfil.tipo_pago
            empleado.sueldo_diario = empleado.perfil.sueldo_base

            empleado.save()
            return super().form_valid(form)




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
        model = NominaEmpleado
        fields = ['proyecto']
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from adm.models import Proyecto
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---"



class SeleccionarPeriodoForm(forms.Form):
    periodo = forms.ModelChoiceField(
        queryset=PeriodosNomina.objects.filter(
            estatus__in=['ABIERTO', 'EN PROCESO']
        ).order_by('-periodo_inicio'),
        label="Período de Nómina",
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'style': 'width:100%;',
        })
    )

    def __init__(self, *args, **kwargs):
        # Recibimos la request para validar sesión
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_periodo(self):
        periodo = self.cleaned_data.get('periodo')

        # Si tenemos acceso al request (vista la pasa como argumento)
        if self.request:
            periodo_actual = self.request.session.get('periodo_id')
            if periodo_actual and str(periodo.id) == str(periodo_actual):
                raise forms.ValidationError(
                    f"⚠️ El período '{periodo}' ya está seleccionado actualmente."
                )

        # Validación adicional: no permitir seleccionar períodos cerrados o cancelados
        if periodo.estatus in ['CERRADO', 'CANCELADO']:
            raise forms.ValidationError(
                f"⚠️ El período '{periodo}' ya está {periodo.estatus.lower()}."
            )

        return periodo

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

class NominaEmpleadoProyectoForm(forms.ModelForm):
    class Meta:
        model = NominaEmpleado
        fields = ['proyecto']
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from adm.models import Proyecto
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---"


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
            'fecha': forms.DateInput(format='%Y-%m-%d',attrs={'type': 'date', 'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2', 'id': 'id_proyecto', 'style': 'width: 100%;'}),
            'horas_trabajadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0', 'max': '12'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from adm.models import Proyecto
        self.fields['empleado'].queryset = Empleado.objects.all()
        self.fields['empleado'].empty_label = "--- Seleccione un Empleado ---"
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proyecto'].empty_label = "--- Seleccione un Proyecto ---"
        self.fields['proyecto'].required = False

        if self.instance and self.instance.pk:
            self.fields['empleado'].initial = self.instance.empleado.pk
            self.fields['proyecto'].initial = self.instance.proyecto.pk if self.instance.proyecto else None
            # Convertir la fecha a formato ISO (cadena)
            if self.instance.fecha:
                self.fields['fecha'].initial = self.instance.fecha.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        fecha = cleaned_data.get('fecha')
        proyecto = cleaned_data.get('proyecto')
        horas_trabajadas = cleaned_data.get('horas_trabajadas')

        # Validar unicidad, incluyendo proyecto=None
        if empleado and fecha:
            query = AsignacionDiaria.objects.filter(
                empleado=empleado,
                fecha=fecha,
                proyecto=proyecto  # Incluye None explícitamente
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise forms.ValidationError(
                    f"Ya existe una asignación para {empleado} en {fecha.strftime('%Y-%m-%d')} "
                    f"con el proyecto {proyecto or 'Sin Proyecto'}."
                )

        # Validar falta en Asistencia
        if empleado and fecha and Asistencia.objects.filter(empleado=empleado, fecha=fecha).exists():
            raise forms.ValidationError("No se puede asignar: Hay una falta registrada para este día.")

        # Validar máximo 12 horas
        if empleado and fecha and horas_trabajadas:
            total_horas = AsignacionDiaria.objects.filter(
                empleado=empleado,
                fecha=fecha
            ).exclude(pk=self.instance.pk if self.instance else None).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
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

# Formset para ítems de requisición

class RegistraAsistenciaForm(forms.ModelForm):
    class Meta:
        model = RegistraAsistencia
        fields = ['fecha_hora_entrada', 'latitud', 'longitud']
        widgets = {
            'fecha_hora_entrada': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control'}),
            
        }



class TipoDestajoForm(forms.ModelForm):
    class Meta:
        model = TipoDestajo
        fields = ["nombre", "unidad"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del destajo"}),
            "unidad": forms.TextInput(attrs={"class": "form-control", "placeholder": "Unidad (m3, pza, viaje, etc.)"}),
        }

class TarifaDestajoObraForm(forms.ModelForm):
    class Meta:
        model = TarifaDestajoObra
        fields = ["obra", "tipo", "tarifa"]
        widgets = {
            "obra": forms.Select(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "tarifa": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }





class HorasExtrasForm(forms.ModelForm):
    class Meta:
        model = HorasExtras
        fields = ['empleado', 'periodo', 'proyecto', 'fecha', 'horas', 'pago_por_hora']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control select2'}),
            'periodo': forms.Select(attrs={'class': 'form-control select2'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'pago_por_hora': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
        }


class CompensacionVariableForm(forms.ModelForm):
    class Meta:
        model = CompensacionVariable
        fields = ['empleado', 'periodo', 'proyecto', 'fecha', 'monto', 'concepto']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control select2'}),
            'periodo': forms.Select(attrs={'class': 'form-control select2'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'concepto': forms.TextInput(attrs={'class': 'form-control'}),
        }



class NominaComparativoFiltroForm(forms.Form):
    TIPO_REPORTE = [
        ("SEMANAL", "Semanas"),
        ("MENSUAL", "Meses"),
        ("PROYECTOS", "Proyectos"),
    ]

    tipo = forms.ChoiceField(choices=TIPO_REPORTE, required=True, label="Comparar por")
    anio = forms.IntegerField(required=False, label="Año")
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.all(),
        required=False,
        label="Proyecto"
    )
    periodo = forms.ModelChoiceField(
        queryset=PeriodosNomina.objects.all().order_by("-periodo_inicio"),
        required=False,
        label="Semana"
    )


from django import forms
from nomina.models import PerfilPuesto


class PerfilPuestoForm(forms.ModelForm):

    class Meta:
        model = PerfilPuesto
        fields = ['nombre', 'categoria', 'sueldo_min', 'sueldo_max', 'activo']

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'sueldo_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sueldo_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()

        min_sueldo = cleaned.get("sueldo_min")
        max_sueldo = cleaned.get("sueldo_max")

        if min_sueldo and max_sueldo:
            if min_sueldo > max_sueldo:
                raise forms.ValidationError("El sueldo mínimo no puede ser mayor al máximo.")

        return cleaned
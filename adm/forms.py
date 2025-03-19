from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import( Cuenta, Banco, Residente, TipoDocumento, Proyecto, Simbologia, 
                     RegistroCuenta, Equipo, Bitacora, TipoPago, Pago)
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


class TipoPagoForm(forms.ModelForm):
    class Meta:
        model = TipoPago
        fields = ['nombre']

    
class BancoForm(forms.ModelForm):
    class Meta:
        model = Banco
        fields = ['nombre']
        labels = {
            'nombre': 'Nombre del Banco:',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }


t_cuenta = [
    ('General', 'General'),
    ('Proyecto', 'Proyecto')
]

class CuentaForm(forms.ModelForm):
    class Meta:
        model = Cuenta
        fields = ['banco', 'cuenta', 'clabe', 'saldo_inicial', 'saldo_actual','estado','tipo_cuenta']        
        labels = {
            'banco': 'Banco:',
            'cuenta': 'Número de Cuenta:',
            'clabe': 'CLABE:',
            'saldo_inicial': 'Saldo Inicial:',
            'saldo_actual': 'Saldo Actual:',
            'estado': 'Estado:',
            'tipo': 'Tipo cuenta:',
        }
        widgets = {
            'banco': forms.Select(attrs={'class': 'form-control'}),
            'cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'clabe': forms.TextInput(attrs={'class': 'form-control'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control'}),
            'saldo_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
        }
        tipo_cuenta = forms.ChoiceField(choices=t_cuenta, label='Tipo de Cuenta', required=True)
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in iter(self.fields):
                self.fields[field].widget.attrs.update({
                'class':'form-control' 
            })


class ResidenteForm(forms.ModelForm):
    class Meta:
        model = Residente
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ingrese el nombre del residente'}),
        }


class TipoDocumentoForm(forms.ModelForm):
    class Meta:
        model = TipoDocumento
        fields = ['tipo', 'movimiento']  # Asegúrate de incluir todos los campos necesarios
        labels = {
            'tipo': 'Tipo de Documento:',
            'movimiento': 'Tipo de Movimiento:',
        }
        widgets = {
            'tipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el tipo de documento'}),
            'movimiento': forms.Select(attrs={'class': 'form-control'}),
        }

class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre', 'ubicacion', 'latitud', 'longitud', 'residente', 'cuenta','mapa']
        labels = {
            'nombre': 'Nombre:',
            'ubicacion': 'Ubicación:',
            'latitud': 'Latitud:',
            'longitud': 'Longitud:',
            'residente': 'Residente:',
            'cuenta': 'Cuenta:',
            'mapa':'Mapa del proyecto:',
        }
        mapa_pdf = forms.FileField(required=False)
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control'}),
            'residente': forms.Select(attrs={'class': 'form-control'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'mapa': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
        
escoge_tipo = [
    ('Padre','Padre'),
    ('Hijo','Hijo')
]
class SimbologiaForm(forms.ModelForm):
    class Meta:
        model = Simbologia
        fields = '__all__'  # Esto incluye todos los campos del modelo. Puedes limitarlo si lo prefieres.
        labels = {
            'origen': 'Familia',
            'clave': 'Consecutivo',
            'descripcion': 'Descripción',
            'abreviatura': 'Abreviatura',
            'estatus': 'Estatus',
            'tipo': 'Tipo',
        }
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la descripción'}),
            'abreviatura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la abreviatura'}),
            'origen': forms.NumberInput(attrs={'class': 'form-control'}),
            'clave': forms.NumberInput(attrs={'class': 'form-control'}),
            'estatus': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
        }
        escoge_tipo = forms.ChoiceField(choices=escoge_tipo, label='Tipo', required=True)






        
        

    
class ReporteMovimientoForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Inicio'
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Fin'
    )    


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['identificador', 'descripcion', 'modelo', 'placas']
        widgets = {
            'identificador':forms.TextInput(attrs={'placeholder':'Identificador'}),
            'descripcion': forms.TextInput(attrs={'placeholder': 'Descripción'}),
            'modelo':forms.TextInput(attrs={'placeholder': 'Modelo'}),
            'placas': forms.TextInput(attrs={'placeholder': 'Placas'}),
        }
    

class BitacoraForm(forms.ModelForm):
    class Meta:
        model = Bitacora
        fields = ['proyecto', 'actividad', 'personal_involucrado', 'maquinaria_utilizada', 'avance', 'material_entregado']
        widgets = {
            'actividad': forms.Textarea(attrs={'rows': 3}),
            'avance': forms.Textarea(attrs={'rows': 3}),
            'material_entregado': forms.Textarea(attrs={'rows': 3}),
        }

class TipoDocumentoForm(forms.ModelForm):
    class Meta:
        model = TipoDocumento
        fields = ['tipo', 'movimiento']
        labels = {
            'tipo': 'Documento',
            'movimiento': 'Tipo de Movimiento',
        }
        widgets = {
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
            'movimiento': forms.Select(attrs={'class': 'form-control'}),
        }


class RegistroCuentaForm(forms.ModelForm):
    class Meta:
        model = RegistroCuenta
        fields = [
            'fecha_movimiento',
            'concepto',
            'cantidad',
            'cuenta',
            'folio_documento',
            'reposicion_flujo',
        ]
        widgets = {
            'fecha_movimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'concepto': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'folio_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'reposicion_flujo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }        


class PagoForm(forms.ModelForm):
    def __init__(self, *args, compra=None, **kwargs):
        super().__init__(*args, **kwargs)
        if compra:
            self.instance.compra = compra  # ✅ Se asigna la compra al formulario

    class Meta:
        model = Pago
        fields = ['tipo_pago', 'monto']
    
    def clean_monto(self):
        monto = self.cleaned_data['monto']
        
        if not self.instance.compra:
            raise forms.ValidationError("El pago no está asociado a ninguna compra.")

        saldo_pendiente = self.instance.compra.saldo_pendiente()
        
        if monto > saldo_pendiente:
            raise forms.ValidationError("El pago excede el saldo pendiente.")
        
        return monto




from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import( Cuenta, ProductoInmobiliario, Venta,
                    Movimiento, Cliente)
from adm.models import Proyecto
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


class ValoresConstantesForm(forms.Form):
    precio = forms.DecimalField(max_digits=10, decimal_places=2, label="Precio")
    medidas = forms.CharField(max_length=100, label="Medidas")
    proyecto = forms.ModelChoiceField(queryset=Proyecto.objects.all(), label="Proyecto")
    cantidad = forms.IntegerField(min_value=1, label="Cantidad de registros")



class ProductoInmobiliarioForm(forms.ModelForm):
    class Meta:
        model = ProductoInmobiliario
        fields = ['clave', 'proyecto', 'proceso', 'precio', 'saldo', 'medidas', 'tipo']
        widgets = {
            'proceso': forms.Select(attrs={'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'clave': forms.HiddenInput(),
            'clave': forms.TextInput(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'saldo': forms.NumberInput(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'medidas': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VentaForm(forms.Form):
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.all(), label="Cliente")

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['monto', 'tipo', 'notas'] 


class AsignarClienteForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['cliente', 'monto']  # Campos del cliente y monto
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'curp', 'identificacion', 'tipo_identificacion', 'telefono', 'email', 'documento_comprobatorio']
        exclude = ['uc_id']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'curp': forms.TextInput(attrs={'class': 'form-control'}),
            'identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_identificacion': forms.Select(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'documento_comprobatorio': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    
    def clean(self):
        cleaned_data = super().clean()
        curp = cleaned_data.get('curp')
        instance = self.instance

        # Validar si el CURP ya existe en otro registro
        if Cliente.objects.filter(curp=curp).exclude(pk=instance.pk).exists():
            raise ValidationError({'curp': "El CURP ya está registrado para otro cliente."})

        return cleaned_data

    # def clean_curp(self):
    #     curp = self.cleaned_data.get('curp')
    #     instance = self.instance  # Registro que se está editando

    #     # Verificar si el CURP existe en otro registro
    #     if Cliente.objects.filter(curp=curp).exclude(pk=instance.pk).exists():
    #         raise ValidationError("El CURP ya está registrado para otro cliente.")
        
    #     return curp
    

    def clean_curp(self):
        curp = self.cleaned_data.get("curp")
        curp_regex = r"^[A-Z]{4}[0-9]{6}[A-Z]{6}[0-9A-Z]{2}$"
        if not re.fullmatch(curp_regex, curp):
            raise forms.ValidationError(
                "La CURP debe tener exactamente 18 caracteres con el formato válido: "
                "4 letras, 6 números, 6 letras y 2 caracteres alfanuméricos."
            )
        return curp



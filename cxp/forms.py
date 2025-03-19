from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import(Proveedor, CompraEnc, CompraDet)
from adm.models import Simbologia
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

class ProveedorForm(forms.ModelForm):
    experiencia = forms.ModelChoiceField(
        queryset=Simbologia.objects.all(),
        label="Experiencia", 
        empty_label="Selecciona una experiencia", 
        widget=Select2Widget(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Proveedor
        fields = ['razon_social', 'domicilio', 'telefono', 'email', 'experiencia']
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'domicilio': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }




class CompraEncForm(forms.ModelForm):
    class Meta:
        model = CompraEnc
        fields = ['proveedor', 'fecha', 'orden_compra','folio_documento','dias_credito', 'proyecto', 'tipo', 'inventario', 'total']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-control select2'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),  # Campo de proyecto como dropdown
            'tipo': forms.Select(attrs={'class': 'form-control select2'}),      # Campo de tipo como dropdown
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'orden_compra': forms.NumberInput(attrs={'class': 'form-control'}),
            'folio_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'dias_credito':forms.NumberInput(attrs={'class': 'form-control'}),
            'inventario': forms.TextInput(attrs={'class': 'form-control'}),
            'total': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class':'form-control'
            })
        # aqui van los campos de solo lectura
        self.fields['total'].widget.attrs['readonly'] = True




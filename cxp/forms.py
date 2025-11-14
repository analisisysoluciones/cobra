from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import(Proveedor, CompraEnc, CompraDet)
from adm.models import Simbologia, Proyecto
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from inv.models import Material # Importar Material
from decimal import Decimal # <--- ¡IMPORTANTE: Añadir esta línea!


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
        # Asegúrate de que todos los campos del modelo que usas en el formulario estén aquí
        fields = [
            'tipo', 'fecha', 'orden_compra', 'folio_documento', 'inventario',
            'proveedor', 'total', 'archivo_pdf', 'proyecto', 'estado',
            'dias_credito', 'fecha_pago', 'estatus_pago',
            'evidencia_recoge', 'evidencia_uso', 'autoriza'
        ]
        widgets = {
            'fecha': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'   # 🚀 Este formato es CLAVE
            ),
            'orden_compra': forms.NumberInput(attrs={'class': 'form-control'}),
            'folio_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'dias_credito': forms.NumberInput(attrs={'class': 'form-control'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}), # Total debe ser de solo lectura
            'tipo': forms.Select(attrs={'class': 'form-control select2'}),
            'proveedor': forms.Select(attrs={'class': 'form-control select2'}),
            'proyecto': forms.Select(attrs={'class': 'form-control select2'}),
            'autoriza': forms.Select(attrs={'class': 'form-control'}),
            
            # Campos de archivo
            'archivo_pdf': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'evidencia_recoge': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'evidencia_uso': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),

            # Campos ocultos o con valores por defecto que no se editan directamente
            'estado': forms.HiddenInput(), 
            'estatus_pago': forms.HiddenInput(), 
            'fecha_pago': forms.HiddenInput(), 
            'inventario': forms.CheckboxInput(attrs={'style': 'display: none;'}), # Tu HTML lo maneja con un span/icono
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%d']

        # Asignar 'form-control' a los campos de texto/número que no tienen un widget específico
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput)):
                current_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in current_classes:
                    field.widget.attrs['class'] = (current_classes + ' form-control').strip()
        
        # El campo 'total' ya se estableció como readonly en los widgets, pero si quieres asegurarte:
        self.fields['total'].widget.attrs['readonly'] = True

    def clean_folio_documento(self):
        folio = self.cleaned_data['folio_documento']
        if folio and folio.lower() not in ['s/n', 'sn'] and CompraEnc.objects.filter(folio_documento=folio).exists():
            raise forms.ValidationError("El folio ya existe.")
        return folio


class CompraDetForm(forms.ModelForm):
    # material_id y descripcion_material no son campos directos del modelo CompraDet
    # pero los necesitamos para la lógica JS y la validación en la vista.
    # El campo 'material' del modelo CompraDet se asignará manualmente en la vista.
    material_id = forms.IntegerField(
        required=False, # Puede ser nulo si no se selecciona un detalle (o si el formulario se envia sin detalle)
        widget=forms.HiddenInput(attrs={'id': 'id_id_producto'}) # Coincide con tu input oculto en HTML
    )
    descripcion_material = forms.CharField(
        required=False, # No es estrictamente requerido para la validación del form, solo para display
        widget=forms.TextInput(attrs={'id': 'id_descripcion_producto', 'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )

    class Meta:
        model = CompraDet
        fields = ['cantidad', 'precio_unitario'] # 'material' se manejará en la vista
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        material_id = cleaned_data.get('material_id')
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precio_unitario')

        # Si se están enviando datos de detalle (al menos el ID del material tiene un valor numérico)
        if material_id is not None and material_id != '':
            # Ahora, como material_id es IntegerField, ya se intentó convertir a int.
            # Si falló, ya estaría en self._errors.

            # Validar que cantidad y precio_unitario no estén vacíos si material_id fue enviado
            if cantidad is None or cantidad == '': # Usa 'is None' para NumberInput cuando está vacío
                self.add_error('cantidad', 'La cantidad es obligatoria cuando se añade un material.')
            elif Decimal(cantidad) <= 0:
                 self.add_error('cantidad', 'La cantidad debe ser mayor a cero.')

            if precio_unitario is None or precio_unitario == '':
                self.add_error('precio_unitario', 'El precio unitario es obligatorio cuando se añade un material.')
            elif Decimal(precio_unitario) <= 0:
                self.add_error('precio_unitario', 'El precio unitario debe ser mayor a cero.')
            
            # Validar si el material existe
            try:
                if material_id is not None: # Solo intentar si material_id no es None
                    Material.objects.get(pk=material_id)
            except Material.DoesNotExist:
                self.add_error('material_id', 'Material no válido.')
            except Exception as e:
                self.add_error('material_id', f'Error al validar material: {e}')
        
        return cleaned_data
    
# forms.py


class FiltroCompraForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False, label='Fecha inicio',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False, label='Fecha fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all(),
        required=False,
        label='Proveedor',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estatus_pago = forms.ChoiceField(
        required=False,
        choices=[('', '--- Todos ---')] + CompraEnc.ESTATUS_PAGO_CHOICES,
        label='Estatus de pago',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.all(),
        required=False,
        label='Proyecto',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean_estatus_pago(self):
        val = self.cleaned_data.get('estatus_pago')
        if val:
            return val.lower().strip()
        return val



class FiltroCompraMatForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False, label='Fecha inicio',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False, label='Fecha fin',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.all().order_by('razon_social'), # Agrega un order_by para mejor visualización
        required=False,
        label='Proveedor',
        empty_label='Todos', # Esto asegurará que el primer elemento sea "Todos"
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    estatus_pago = forms.ChoiceField(
        required=False,
        choices=[('', '--- Todos ---')] + CompraEnc.ESTATUS_PAGO_CHOICES,
        label='Estatus de pago',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.all().order_by('nombre'), # Asumo que Proyecto tiene un campo 'nombre'
        required=False,
        label='Proyecto',
        empty_label='Todos',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

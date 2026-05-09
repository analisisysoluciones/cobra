from django import forms
from .models import Categoria, Material, Unidad, Requisicion, ItemRequisicion, Firma, SalidaAlmacen, SalidaAlmacenD
from adm.models import Proyecto
from nomina.models import Empleado
from django.forms import inlineformset_factory



class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['descripcion', 'estado']
        labels = {
            'descripcion': 'Descripción de la Categoria:',
            'estado': 'Estado:'
        }
        widget = {'descripcion':forms.TextInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class':'form-control' 
            })


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = ['clave', 'descripcion']
        labels = {
            'clave': 'Unidad:',
            'descripcion': 'Descripción:'
        }
        widgets = {
            'clave': forms.TextInput(),
            'descripcion': forms.TextInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })



class MaterialForm(forms.ModelForm):

    class Meta:
        model = Material
        fields = [
            'clave',
            'descripcion',
            'unidad_medida',
            'tipo_insumo',   # 👈 NUEVO CAMPO
            'existencia',
            'maximo',
            'minimo',
        ]

        labels = {
            'clave': 'Clave:',
            'descripcion': 'Descripción:',
            'unidad_medida': 'Unidad de Medida:',
            'tipo_insumo': 'Tipo de Insumo:',   # 👈 NUEVO
            'existencia': 'Existencia:',
            'maximo': 'Máximo:',
            'minimo': 'Mínimo:',
        }

        widgets = {
            'clave': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-select'}),
            'tipo_insumo': forms.Select(attrs={'class': 'form-select'}),  # 👈 NUEVO
            'existencia': forms.NumberInput(attrs={'class': 'form-control'}),
            'maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'minimo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)





class RequisicionForm(forms.ModelForm):
    class Meta:
        model = Requisicion
        fields = ['solicitante', 'proyecto', 'comentarios']
        widgets = {
            'solicitante': forms.Select(attrs={'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'comentarios': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['solicitante'].queryset = Empleado.objects.filter(estado=True)
        self.fields['proyecto'].queryset = Proyecto.objects.all()  # 🔹 agrega esto
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ItemRequisicionForm(forms.ModelForm):
    material_id = forms.IntegerField(required=False, widget=forms.HiddenInput(attrs={'id': 'id_material', 'name': 'material_id'}))
    descripcion_material = forms.CharField(required=False, widget=forms.TextInput(attrs={'id': 'id_descripcion_material', 'readonly': 'readonly', 'class': 'form-control-plaintext'}))

    class Meta:
        model = ItemRequisicion
        fields = ['cantidad_solicitada', 'cantidad_entregada', 'verificado']
        widgets = {
            'cantidad_solicitada': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'name': 'cantidad_solicitada'}),
            'cantidad_entregada': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'name': 'cantidad_entregada'}),
            'verificado': forms.CheckboxInput(attrs={'class': 'form-check-input', 'name': 'verificado'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        material_id = cleaned_data.get('material_id')
        cantidad_solicitada = cleaned_data.get('cantidad_solicitada')
        cantidad_entregada = cleaned_data.get('cantidad_entregada')

        if material_id:
            if cantidad_solicitada is None or cantidad_solicitada <= 0:
                self.add_error('cantidad_solicitada', 'La cantidad solicitada es obligatoria y debe ser mayor a cero.')
            if cantidad_entregada is not None and cantidad_entregada < 0:
                self.add_error('cantidad_entregada', 'La cantidad entregada no puede ser negativa.')
            try:
                material = Material.objects.get(pk=material_id)
                if cantidad_entregada and cantidad_entregada > material.stock_actual:
                    self.add_error('cantidad_entregada', f'No hay suficiente stock para {material.nombre}. Stock actual: {material.stock_actual}.')
            except Material.DoesNotExist:
                self.add_error('material_id', 'Material no válido.')
        return cleaned_data

class FirmaForm(forms.ModelForm):
    
    class Meta:
        model = Firma
        fields = ['empleado', 'imagen_firma', 'comentarios']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-control'}),
            'imagen_firma': forms.FileInput(attrs={'class': 'form-control-file'}),
            'comentarios': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.filter(estado=True)



class RequisicionFilterForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    estatus = forms.ChoiceField(
        choices=[('', '--- Todos ---')] + list(Requisicion._meta.get_field('estatus').choices),
        required=False
    )
    solicitante = forms.ModelChoiceField(
        queryset=Empleado.objects.all(),
        required=False,
        empty_label="--- Todos ---"
    )


class SalidaAlmacenForm(forms.ModelForm):

    class Meta:
        model = SalidaAlmacen
        fields = ['fecha', 'equipo',  'observaciones']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SalidaAlmacenDetalleForm(forms.ModelForm):

    class Meta:
        model = SalidaAlmacenD
        fields = ['material', 'cantidad']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }

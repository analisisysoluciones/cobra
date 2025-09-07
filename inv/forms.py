from django import forms
from .models import Categoria, Material, Unidad, Requisicion, ItemRequisicion, Firma
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
        fields = ['clave', 'descripcion', 'unidad_medida', 'existencia', 'maximo', 'minimo']  # Elimina 'estado' si no existe
        labels = {
            'clave': 'Clave:',
            'descripcion': 'Descripción:',
            'unidad_medida': 'Unidad de Medida:',
            'existencia': 'Existencia:',
            'maximo': 'Máximo:',
            'minimo': 'Mínimo:',
        }
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}),
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

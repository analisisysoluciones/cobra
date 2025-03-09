from django import forms
from .models import Categoria, Material, Unidad


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














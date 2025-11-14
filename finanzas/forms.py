from django import forms
from .models import IngresoExtraordinario
from adm.models import Proyecto, Cuenta

class IngresoExtraForm(forms.ModelForm):
    class Meta:
        model = IngresoExtraordinario
        fields = [
            "fecha", "cuenta", "proyecto", "tipo",
            "concepto", "referencia", "monto"
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "cuenta": forms.Select(attrs={"class": "form-control"}),
            "proyecto": forms.Select(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "concepto": forms.TextInput(attrs={"class": "form-control"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class IngresoExtraFiltroForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    cuenta = forms.ModelChoiceField(
        queryset=Cuenta.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    tipo = forms.ChoiceField(
        choices=[("", "Todos los tipos")] + IngresoExtraordinario.TIPO_INGRESO,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )

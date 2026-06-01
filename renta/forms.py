from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import(RentaEquipo, Cliente, TarifaEquipo, RentaConcepto, ConceptoRentaCatalogo, PagoRenta)
from .constants import TRANSICIONES_VALIDAS
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.forms import inlineformset_factory


#──────
# forms.py  — sección RentaEquipoForm
# ─────────────────────────────────────────────

from django import forms
# Elimina: from django_select2.forms import Select2Widget

class RentaEquipoForm(forms.ModelForm):
    class Meta:
        model = RentaEquipo
        fields = [
            "cliente", "equipo", "tarifa",
            "fecha_inicio", "fecha_fin", "observaciones","estatus",
        ]
        widgets = {
            "cliente": forms.Select(attrs={
                "class": "form-control select2",
                "data-placeholder": "Buscar cliente...",
            }),
            "equipo": forms.Select(attrs={
                "class": "form-control select2",
                "data-placeholder": "Buscar equipo...",
            }),
            "estatus": forms.Select(attrs={
                "class": "form-control",
            }),
            "tarifa": forms.Select(attrs={
                "class": "form-control select2",
                "data-placeholder": "Buscar tarifa...",
            }),
            "fecha_inicio": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "fecha_fin": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }, format="%Y-%m-%dT%H:%M"),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }
        
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            # EDICIÓN: quita estatus del form, se maneja con botón
            self.fields.pop("estatus")
        else:
            # CREACIÓN: solo permite elegir COTIZACION o ACTIVA
            self.fields["estatus"].choices = [
                ("COTIZACION", "Cotización"),
                ("ACTIVA",     "Renta directa"),
            ]

        # Fechas
        if self.instance.fecha_inicio:
            self.initial["fecha_inicio"] = (
                self.instance.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
            )
        if self.instance.fecha_fin:
            self.initial["fecha_fin"] = (
                self.instance.fecha_fin.strftime("%Y-%m-%dT%H:%M")
            )
# ─────────────────────────────────────────────
# forms.py  — formset con prefijo explícito
# ─────────────────────────────────────────────

                
                
                
class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "telefono",
            "email",
            "direccion",
            "rfc",
            "activo",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del cliente"
            }),

            "telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Teléfono"
            }),

            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Correo electrónico"
            }),

            "direccion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Dirección"
            }),

            "rfc": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "RFC"
            }),

            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "role": "switch",
                "style": "width:42px;height:24px;cursor:pointer;"
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre")

        existe = Cliente.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)

        if existe.exists():
            raise forms.ValidationError("Ya existe un cliente con este nombre.")

        return nombre


class TarifaEquipoForm(forms.ModelForm):

    class Meta:
        model = TarifaEquipo
        fields = [
            "equipo",
            "tipo_cobro",
            "precio",
            "activo",
        ]

        widgets = {
            "equipo": forms.Select(
                attrs={
                    "class": "form-control select2"
                }
            ),

            "tipo_cobro": forms.Select(attrs={
                "class": "form-control"
            }),

            "precio": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "Ej: 850.00"
            }),

            "activo": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    # 🔥 VALIDACIÓN CLAVE (evita duplicados)
    def clean(self):
        cleaned = super().clean()

        equipo = cleaned.get("equipo")
        tipo_cobro = cleaned.get("tipo_cobro")

        if equipo and tipo_cobro:
            existe = TarifaEquipo.objects.filter(
                equipo=equipo,
                tipo_cobro=tipo_cobro
            )

            # si es edición, excluye el mismo registro
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)

            if existe.exists():
                raise forms.ValidationError(
                    "Ya existe una tarifa para este equipo y tipo de cobro."
                )

        return cleaned        


class RentaConceptoForm(forms.ModelForm):

    class Meta:

        model = RentaConcepto

        fields = [
            "concepto",
            "cantidad",
            "precio",
            "observaciones",
        ]

        widgets = {

            "concepto": forms.Select(
                attrs={
                    "class": "form-control concepto-select"
                }
            ),

            "cantidad": forms.NumberInput(
                attrs={
                    "class": "form-control cantidad-input",
                    "step": "0.01"
                }
            ),

            "precio": forms.NumberInput(
                attrs={
                    "class": "form-control precio-input",
                    "step": "0.01"
                }
            ),

            "observaciones": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

        }
RentaConceptoFormSet = inlineformset_factory(
    RentaEquipo,
    RentaConcepto,
    form=RentaConceptoForm,
    extra=1,
    can_delete=True,
    
    
)


# FIX: prefijo fijo para que el template y el JS lo conozcan siempre

class PagoRentaForm(forms.ModelForm):

    class Meta:

        model = PagoRenta

        fields = [

            "metodo_pago",
            "referencia",
            "importe",
            "observaciones"

        ]

        widgets = {

            "metodo_pago": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "referencia": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Referencia"
                }
            ),

            "importe": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01"
                }
            ),

            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),

        }
        
        
class ConceptoRentaCatalogoForm(forms.ModelForm):

    class Meta:

        model = ConceptoRentaCatalogo

        fields = [

            "nombre",
            "precio_default",
            "activo"

        ]

        widgets = {

            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "precio_default": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01"
                }
            ),

            "activo": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

        }
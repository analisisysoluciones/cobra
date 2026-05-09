from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import(RentaEquipo, Cliente, TarifaEquipo)

from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta


class RentaEquipoForm(forms.ModelForm):

    class Meta:
        model = RentaEquipo
        fields = [
            "cliente",
            "equipo",
            "tarifa",
            "fecha_inicio",
            "fecha_fin",
            "observaciones",
        ]

        widgets = {   # 🔥 AQUÍ DENTRO
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),

            "tarifa": forms.Select(attrs={
                "class": "form-control",
                "id": "id_tarifa"
            }),

            "cantidad": forms.NumberInput(attrs={
                "class": "form-control",
                "id": "id_cantidad"
            }),
        }

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
            "equipo": forms.Select(attrs={
                "class": "form-control"
            }),

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
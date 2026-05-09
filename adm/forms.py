from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import( Cuenta, Banco, Residente, TipoDocumento, Proyecto, Simbologia, 
                     RegistroCuenta, Equipo, Bitacora, TipoPago, Pago, DocumentoGeneral, 
                     CargaCombustible, ReporteEquipo, PagoIndirecto, OrdenServicio, ReporteEquipoPDA, MantenimientoEquipo,
                     TipoEquipo, ActividadEquipo, ReporteEquipoDetalle
                   ) #CostoProyecto)
from cxp.models import Proveedor
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta



class TipoPagoForm(forms.ModelForm):
    class Meta:
        model = TipoPago
        fields = ['nombre']

 



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
        fields = ['nombre', 'ubicacion', 'latitud', 'longitud', 'residente', 'cuenta','mapa','presupuesto']
        labels = {
            'nombre': 'Nombre:',
            'ubicacion': 'Ubicación:',
            'latitud': 'Latitud:',
            'longitud': 'Longitud:',
            'residente': 'Residente:',
            'cuenta': 'Cuenta:',
            'mapa':'Mapa del proyecto:',
            'presupuesto':'Presupuesto:'
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
            'presupuesto': forms.NumberInput(attrs={'class': 'form-control'}),
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

class DocumentoGeneralForm(forms.ModelForm):
    class Meta:
        model = DocumentoGeneral
        fields = ['tipo', 'descripcion', 'archivo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }





        
        

    
class ReporteMovimientoForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Inicio'
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha Fin'
    )    


# forms.py

class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            'identificador',
            'descripcion',
            'modelo',
            'placas',
            'tipo_equipo',
            'tipo_control',
            'tipo',
        ]

        widgets = {
            'identificador': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Identificador'
            }),

            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción'
            }),

            'modelo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Modelo'
            }),

            'placas': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Placas'
            }),

            'tipo_equipo': forms.Select(attrs={
                'class': 'form-control'
            }),

            'tipo_control': forms.Select(attrs={
                'class': 'form-control'
            }),

            'tipo': forms.Select(attrs={
                'class': 'form-control'
            }),
        }



        
class BitacoraForm(forms.ModelForm):
    class Meta:
        model = Bitacora
        fields = ['proyecto', 'fecha', 'contenido', 'documento']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
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
        fields = ['tipo_pago', 'monto', 'cuenta_bancaria']
        widgets = {
            'cuenta_bancaria': forms.Select(attrs={'class': 'form-control'}),  # Aplica un estilo si usas Bootstrap
        }
    
    def clean_monto(self):
        monto = self.cleaned_data['monto']
        
        if not self.instance.compra:
            raise forms.ValidationError("El pago no está asociado a ninguna compra.")

        saldo_pendiente = self.instance.compra.saldo_pendiente()
        
        if monto > saldo_pendiente:
            raise forms.ValidationError("El pago excede el saldo pendiente.")
        
        return monto


# class CostoProyectoForm(forms.ModelForm):
#     class Meta:
#         model = CostoProyecto
#         fields = ['proyecto', 'descripcion', 'monto', 'movimiento']


class DocumentoGeneralForm(forms.ModelForm):
    class Meta:
        model = DocumentoGeneral
        fields = ['tipo', 'descripcion', 'archivo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class BancoForm(forms.ModelForm):
    class Meta:
        model = Banco
        fields = ['nombre']  # o los campos que quieras


class CargaCombustibleForm(forms.ModelForm):
    class Meta:
        model = CargaCombustible
        fields = [
            'proyecto',          # ← AGREGADO
            'equipo',
            'fecha_carga',
            'tipo_combustible',
            'cantidad_litros',
            'costo_total',
            'odometro',
            'operador',
            'hora',
            'observaciones',
            'folio',
        ]
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control'}),  # ← WIDGET
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_carga': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'tipo_combustible': forms.Select(attrs={'class': 'form-control'}),
            'cantidad_litros': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'odometro': forms.NumberInput(attrs={'class': 'form-control'}),
            'operador': forms.TextInput(attrs={'class': 'form-control'}),
            'hora': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'folio': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtramos/ordenamos si se requiere (puedes ajustarlo)
        self.fields['equipo'].queryset = Equipo.objects.all()
        self.fields['proyecto'].queryset = Proyecto.objects.all().order_by('nombre')

        # Formato de fecha
        self.fields['fecha_carga'].input_formats = ['%Y-%m-%d']

    def clean(self):
        cleaned = super().clean()

        equipo = cleaned.get("equipo")
        fecha = cleaned.get("fecha_carga")
        folio = cleaned.get("folio")



        litros = cleaned.get("cantidad_litros") or 0
        precio = cleaned.get("precio_litro") or 0

        total = litros * precio

        cleaned["costo_total"] = round(total, 2)


        if equipo and fecha and folio:
            qs = CargaCombustible.objects.filter(
                equipo=equipo,
                fecha_carga=fecha,
                folio=folio
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "Ya existe una carga registrada con ese folio para ese equipo."
                )
        return cleaned

    def clean_fecha_carga(self):
        fecha = self.cleaned_data.get("fecha_carga")
        hoy = timezone.now().date()

        if fecha > hoy:
            raise forms.ValidationError(
                "La fecha de carga no puede ser mayor a la fecha actual."
            )

        return fecha
    
    def clean_folio(self):
        folio = (self.cleaned_data.get("folio") or "").strip().upper()

        if not folio:
            raise forms.ValidationError("El folio es obligatorio")

        return folio

class FiltroCombustibleForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Desde", 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    fecha_fin = forms.DateField(
        label="Hasta", 
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    equipo = forms.ModelChoiceField(
        queryset=Equipo.objects.all(), 
        required=False, 
        label="Equipo o Vehículo"
    )
    operador = forms.CharField(
        max_length=80, 
        required=False, 
        label="Operador (Conductor)"
    )

    TIPO_COMBUSTIBLE_CHOICES = [
    ('', '---------'),
    ('gasolina', 'Gasolina'),
    ('diesel', 'Diésel'),
    ]

    tipo_combustible = forms.ChoiceField(
        choices=TIPO_COMBUSTIBLE_CHOICES,
        required=False,
        label='Tipo de Combustible',
    )




class ReporteEquipoForm(forms.ModelForm):
    class Meta:
        model = ReporteEquipo
        fields = [
            'fecha',
            'Proyecto',  # con mayúscula según tu modelo
            'equipo',
            'operador',
            'actividad',
            'horas',
            'diesel_carga',
            'diesel_resta',
            'fallas',
            'observa',  # nombre real del campo
        ]
        labels = {
            'fecha': 'Fecha del Reporte',
            'Proyecto': 'Proyecto',
            'equipo': 'Equipo',
            'operador': 'Operador',
            'actividad': 'Actividad Realizada',
            'horas': 'Horas Trabajadas',
            'diesel_carga': 'Litros Diesel Cargados',
            'diesel_resta': 'Litros Diesel Restantes',
            'fallas': 'Fallas Presentadas',
            'observa': 'Observaciones Adicionales',
        }
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'Proyecto': forms.Select(attrs={'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'operador': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del operador'}),
            'actividad': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción de la actividad'}),
            'horas': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 8.5',
                'step': '0.01',   # ← CLAVE
                'min': '0'
            }),

            'diesel_carga': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 150.00'}),
            'diesel_resta': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 20.00'}),
            'fallas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Si hubo fallas, descríbelas aquí'}),
            'observa': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Cualquier otra observación relevante'}),
        }



class PagoIndirectoForm(forms.ModelForm):
    class Meta:
        model = PagoIndirecto
        fields = ['proyecto', 'proveedor', 'descripcion', 'monto', 'fecha', 'tipo_pago', 'documento', 'folio_documento', 'comprobante']
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción del gasto'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-control'}),
            'documento': forms.Select(attrs={'class': 'form-control'}),
            'folio_documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Folio o s/n'}),
            'comprobante': forms.FileInput(attrs={'class': 'form-control bg-dark text-light border-secondary', 'accept': 'application/pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.all()
        self.fields['proveedor'].queryset = Proveedor.objects.all()
        self.fields['documento'].queryset = TipoDocumento.objects.all()
        self.fields['documento'].required = False
        self.fields['comprobante'].required = False

    def clean_folio_documento(self):
        folio = self.cleaned_data['folio_documento']
        documento = self.cleaned_data['documento']
        if folio and folio.lower() != 's/n' and documento:
            if PagoIndirecto.objects.filter(folio_documento=folio, documento=documento).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("El folio ya está en uso para este tipo de documento.")
        return folio

    def clean_comprobante(self):
        comprobante = self.cleaned_data.get('comprobante')
        if comprobante and not comprobante.name.endswith('.pdf'):
            raise forms.ValidationError("El archivo debe ser un PDF.")
        return comprobante
    

class FiltroReporteEquipoForm(forms.Form):
    fecha_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    proyecto = forms.ModelChoiceField(queryset=Proyecto.objects.all(), required=False)
    equipo = forms.ModelChoiceField(queryset=Equipo.objects.all(), required=False)


# operacion/forms/orden_servicio_form.py


class OrdenServicioForm(forms.ModelForm):

    class Meta:
        model = OrdenServicio
        fields = [
            'fecha',
            'equipo',
            'proveedor',
            'tipo_servicio',
            'descripcion_falla',
            'observaciones',
        ]

        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'tipo_servicio': forms.Select(attrs={'class': 'form-control'}),
            'descripcion_falla': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

        
        def clean(self):
            cleaned = super().clean()

            equipo = cleaned.get("equipo")
            proveedor = cleaned.get("proveedor")
            descripcion = cleaned.get("descripcion_falla")

            if not equipo or not proveedor or not descripcion:
                return cleaned

            hace_10s = timezone.now() - timedelta(seconds=10)

            existe = OrdenServicio.objects.filter(
                equipo=equipo,
                proveedor=proveedor,
                descripcion_falla__iexact=descripcion.strip(),
                creado__gte=hace_10s
            ).exists()

            if existe:
                raise ValidationError(
                    "Posible duplicado detectado. Espere unos segundos."
                )

            return cleaned




# forms.py


class ReporteEquipoForm(forms.ModelForm):
    class Meta:
        model = ReporteEquipoPDA
        fields = ['equipo']



class MantenimientoEquipoForm(forms.ModelForm):
    class Meta:
        model = MantenimientoEquipo
        fields = ['equipo', 'fecha', 'tipo', 'descripcion', 'costo']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
        }        


# nomina/forms.py o adm/forms.py (según dónde lo tengas)



class TipoEquipoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipo
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'})
        }


class ActividadEquipoForm(forms.ModelForm):
    class Meta:
        model = ActividadEquipo
        fields = ['nombre', 'tipo', 'tipos_equipo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'tipos_equipo': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }        


# forms.py



class AbrirJornadaForm(forms.Form):
    equipo = forms.ModelChoiceField(
        queryset=Equipo.objects.all().order_by("descripcion"),
        widget=forms.Select(attrs={
            "class": "form-control select2"
        })
    )



from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import ReporteEquipoDetalle


class ActividadDetalleForm(forms.ModelForm):

    class Meta:
        model = ReporteEquipoDetalle
        fields = [
            "actividad",
            "inicio",
            "fin",
            "proyecto",
            "observaciones",
        ]

        widgets = {
            "actividad": forms.Select(attrs={
                "class": "form-control"
            }),

            "inicio": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control"
                }
            ),

            "fin": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control"
                }
            ),

            "proyecto": forms.Select(attrs={
                "class": "form-control"
            }),

            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2
            }),
        }

    # 🔥 FORMATO CORRECTO PARA HTML5 datetime-local
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ajustar formato de entrada/salida
        self.fields["inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["fin"].input_formats = ["%Y-%m-%dT%H:%M"]

        # Para que al editar se vea correctamente
        if self.instance and self.instance.pk:
            if self.instance.inicio:
                self.initial["inicio"] = self.instance.inicio.strftime("%Y-%m-%dT%H:%M")
            if self.instance.fin:
                self.initial["fin"] = self.instance.fin.strftime("%Y-%m-%dT%H:%M")

    # 🔥 VALIDACIONES + CÁLCULO
    def clean(self):
        cleaned = super().clean()

        inicio = cleaned.get("inicio")
        fin = cleaned.get("fin")
        proyecto = cleaned.get("proyecto")

        # ❌ Proyecto obligatorio
        if not proyecto:
            raise ValidationError("Debe seleccionar un proyecto.")

        # ❌ Validación de tiempos
        if inicio and fin:
            if fin <= inicio:
                raise ValidationError(
                    "La hora final debe ser mayor a la inicial."
                )

            # 🔥 CÁLCULO AUTOMÁTICO DE HORAS
            delta = fin - inicio
            horas = round(delta.total_seconds() / 3600, 2)

            # Guardamos en cleaned_data (no en instancia aún)
            cleaned["horas"] = horas

        return cleaned

    # 🔥 FORZAR GUARDADO DE HORAS
    def save(self, commit=True):
        instance = super().save(commit=False)

        inicio = self.cleaned_data.get("inicio")
        fin = self.cleaned_data.get("fin")

        if inicio and fin:
            delta = fin - inicio
            instance.horas = round(delta.total_seconds() / 3600, 2)

        if commit:
            instance.save()

        return instance

class EscritorioActividadForm(forms.Form):

    actividad = forms.ModelChoiceField(
        queryset=ActividadEquipo.objects.filter(
            activo=True
        ).order_by("nombre"),
        empty_label="Seleccione actividad",
        widget=forms.Select(attrs={
            "class": "form-control",
            "id": "id_actividad"
        })
    )        



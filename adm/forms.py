from django import forms
import datetime
from django.core.exceptions import ValidationError
from .models import( Cuenta, Banco, Residente, TipoDocumento, Proyecto, Simbologia, 
                     RegistroCuenta, Equipo, Bitacora, TipoPago, Pago, DocumentoGeneral, 
                     CargaCombustible, ReporteEquipo, PagoIndirecto) #CostoProyecto)
from cxp.models import Proveedor
from django_select2.forms import Select2Widget
from django.shortcuts import render, redirect
import re
from django.http import JsonResponse
from django.shortcuts import get_object_or_404


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


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['identificador', 'descripcion', 'modelo', 'placas']
        widgets = {
            'identificador':forms.TextInput(attrs={'placeholder':'Identificador'}),
            'descripcion': forms.TextInput(attrs={'placeholder': 'Descripción'}),
            'modelo':forms.TextInput(attrs={'placeholder': 'Modelo'}),
            'placas': forms.TextInput(attrs={'placeholder': 'Placas'}),
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
            'equipo',
            'fecha_carga',
            'tipo_combustible',
            'cantidad_litros',
            'costo_total',
            'odometro',
            'operador',
            'hora',
            'observaciones',
        ]
        widgets = {
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_carga': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'   # <-- AQUÍ el formato que el input espera
            ),
            'tipo_combustible': forms.Select(attrs={'class': 'form-control'}),
            'cantidad_litros': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'odometro': forms.NumberInput(attrs={'class': 'form-control'}),
            'operador': forms.TextInput(attrs={'class': 'form-control'}),
            'hora': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows':3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Opcional: filtrar o ajustar queryset si es necesario
        self.fields['equipo'].queryset = Equipo.objects.all()  #
        self.fields['fecha_carga'].input_formats = ['%Y-%m-%d']


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
            'horas': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 8.5'}),
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
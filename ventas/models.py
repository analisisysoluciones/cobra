from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
import re
from django.utils import timezone
from datetime import date, timedelta
from adm.models import Cuenta, Proyecto


# Create your models here.
def validar_curp(value):
    # Regex para validar el formato de la CURP
    curp_regex = r"^[A-Z]{4}[0-9]{6}[A-Z]{6}[0-9A-Z]{2}$"
    if not re.fullmatch(curp_regex, value):
        raise ValidationError(
            "La CURP debe tener exactamente 18 caracteres con el formato válido: "
            "4 letras, 6 números, 6 letras y 2 caracteres alfanuméricos."
        )
        

tipo_identifacion = [
    ('IFE','IFE'),
    ('PASAPORTE','PASAPORTE'),
]
class Cliente(ClaseModelo):
    fecha_registro = models.DateField('Fecha registro',auto_now_add=True)
    nombre = models.CharField('Nombre',max_length=120,blank=False,null=False,default='')
    curp = models.CharField('Curp',max_length=18,blank=False,null=False,default='', unique=True, validators=[validar_curp],
        help_text="La CURP debe ser única y cumplir con el formato exacto.")
    identificacion = models.CharField('Folio identificación',max_length=30,blank=False,null=False,default='')
    tipo_identificacion = models.CharField('Tipo identificacion',choices=tipo_identifacion,default='IFE')  
    telefono = models.CharField('Telefono', max_length=10,blank=True,null=True,default='')                                         
    email = models.EmailField('Email',blank=True,null=True,default='@gmail.com')
    documento_comprobatorio = models.FileField('Documento', upload_to='expediente/pdfs/',blank=True, null=True)
    
       
    def __str__(self):
        return self.nombre
    
    def clean_curp(self):
        curp = self.cleaned_data.get('curp')
        instance = self.instance

        # Verificar si el CURP ya existe en otro cliente
        if Cliente.objects.filter(curp=curp).exclude(pk=instance.pk).exists():
            raise ValidationError("El CURP ya está registrado para otro cliente.")

        return curp
    
    def clean(self):
        if Cliente.objects.filter(curp=self.curp).exclude(pk=self.pk).exists():
            raise ValidationError("El CURP ya está registrado para otro cliente.")

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.curp = self.curp.upper()
        self.clean()
        super().save(*args, **kwargs)
    
        
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        

proceso_choices =[
    ('Disponible','Disponible'),
    ('Apartado','Apartado'),
    ('Bloqueado','Bloqueado'),
    ('Vendido','Vendido'),
    ('Escrituras','Escrituras'),
    ('Entregado','Entregado'),    
]        
        
class ProductoInmobiliario(ClaseModelo):
    clave = models.IntegerField('Clave',blank=True,null=True)
    proyecto = models.ForeignKey(Proyecto,on_delete=models.CASCADE)
    proceso = models.CharField('Proceso',choices=proceso_choices,default='Disponible')
    precio = models.DecimalField('Precio',max_digits=12,decimal_places=2,default=0.00)
    saldo  = models.DecimalField('Saldo',max_digits=12,decimal_places=2,default=0.00, blank=True,null=True)
    medidas = models.CharField('Medidas', max_length=50, blank=True, null=True)
    tipo = models.IntegerField('Tipo', blank=True,null=True,default=1)
    
    def __str__(self):
        return str(self.clave) + ' ' + str(self.proyecto)
    
    def save(self, *args, **kwargs):
    # self.clave = self.clave.upper()  # Esto no es válido para IntegerField
        super(ProductoInmobiliario, self).save(*args, **kwargs)

    
    class Meta:
        verbose_name = 'Producto inmobiliario'
        verbose_name_plural = 'Productos inmobiliarios'


class Venta(ClaseModelo):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoInmobiliario, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    anticipo = models.DecimalField('Anticipo', max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField('Total', max_digits=12, decimal_places=2)
    saldo_pendiente = models.DecimalField('Saldo Pendiente', max_digits=12, decimal_places=2, default=0.00)
    tipo_pago = models.CharField(
        max_length=20,
        choices=[('Contado', 'Contado'), ('Enganche', 'Enganche'),('Meses', 'Meses')],
        default='Contado'
    )

    def save(self, *args, **kwargs):
        # Restar el anticipo del saldo del inmueble
        self.saldo_pendiente = self.total - self.anticipo
        self.producto.saldo -= self.anticipo
        self.producto.proceso = 'Vendido'  # Cambiar el estado del producto
        self.producto.save()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'


class Movimiento(ClaseModelo):
    producto = models.ForeignKey('ProductoInmobiliario', on_delete=models.CASCADE)
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=50, choices=[('Pago', 'Pago'), ('Anticipo', 'Anticipo'), ('Abono', 'Abono')])
    notas = models.TextField(blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # Fecha del movimiento
    evidencia_pago = models.FileField(upload_to='evidencias_pagos/', blank=True, null=True)  # Archivo del pago
    

    def __str__(self):
        return f'{self.cliente} - {self.monto} ({self.fecha_movimiento})'
    

class ReciboPago(ClaseModelo):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    numero_pago = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=[('Pendiente', 'Pendiente'), ('Pagado', 'Pagado')],
        default='Pendiente'
    )



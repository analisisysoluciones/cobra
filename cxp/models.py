from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo
from inv.models import Material
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
import re
from django.utils import timezone
from datetime import date, timedelta
from django.apps import apps



# Create your models here.


class Proveedor(ClaseModelo):
    razon_social = models.CharField('Razon social',max_length=120,blank=False,null=False)
    domicilio = models.CharField('Domicilio',max_length=120,blank=False,null=False)
    telefono = models.CharField('Telefono',max_length=45)
    email = models.EmailField('Email')
    experiencia = models.ForeignKey('adm.Simbologia',on_delete=models.CASCADE)

    def obtener_simbologia(self):
        Simbologia = apps.get_model('adm', 'Simbologia')  # 🔹 Evita el import circular
        return Simbologia.objects.all()
    
    def save(self):
        self.razon_social = self.razon_social.upper()
        self.domicilio = self.domicilio.upper()
        super(Proveedor, self).save()
    
    def __str__(self):
        return self.razon_social


class CompraEnc(ClaseModelo):
    tipo = models.ForeignKey('adm.TipoDocumento', on_delete=models.CASCADE, related_name='documentos')
    fecha = models.DateField()
    orden_compra = models.IntegerField('Orden de Compra',blank=True,null=True,default=0)
    folio_documento = models.CharField('Folio Documento',max_length=25,blank=False,null=False,default='S/N')
    inventario = models.BooleanField('inventario:', default=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='documentos')
    total = models.DecimalField('total:', max_digits=12, decimal_places=2, default=0.00)
    archivo_pdf = models.FileField('archivo pdf:', upload_to='documentos/pdfs/', blank=True, null=True)
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.CASCADE, related_name='documentos')
    estado = models.CharField('Estado',default='Pendiente',max_length=15)
    dias_credito = models.PositiveIntegerField('Días de Crédito', default=0, blank=True, null=True)
    fecha_pago = models.DateField('Fecha de Pago', blank=True, null=True)

    ESTATUS_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('proximo_vencer', 'Próximo a vencer'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
    ]
    estatus_pago = models.CharField('Estatus de Pago', max_length=15, choices=ESTATUS_PAGO_CHOICES, default='pendiente')

    def saldo_pendiente(self):
        pagos_realizados = self.pagos.aggregate(models.Sum('monto'))['monto__sum'] or 0
        return self.total - pagos_realizados


    def calcular_fecha_pago(self):
        """ Calcula la fecha de pago sumando los días de crédito a la fecha de la compra """
        if isinstance(self.fecha, date) and self.dias_credito is not None:
            try:
                dias_credito_int = int(self.dias_credito)  # Convertimos a entero
                return self.fecha + timedelta(days=dias_credito_int)  # Sumamos días
            except (ValueError, TypeError) as e:
                print(f"Error al calcular fecha de pago: {e}")
                return self.fecha  # Si hay error, usamos la misma fecha
        return self.fecha


    def calcular_estatus_pago(self):
        
        hoy = date.today()
        print(f"self.fecha_pago: {self.fecha_pago}, type: {type(self.fecha_pago)}") #agregado
        if self.fecha_pago:
            if hoy > date.fromisoformat(self.fecha_pago):
                return 'vencido'
            elif hoy >= self.fecha_pago - timedelta(days=5):
                return 'proximo_vencer'
        return 'pendiente'

    """ def save(self, *args, **kwargs):
        self.fecha_pago = self.calcular_fecha_pago()
        
        # Verifica que `fecha_pago` se almacene como `date`
        if isinstance(self.fecha_pago, str):
            try:
                self.fecha_pago = date.fromisoformat(self.fecha_pago)
            except ValueError:
                print(f"Error al convertir fecha_pago antes de guardar: {self.fecha_pago}")
        
        self.estatus_pago = self.calcular_estatus_pago()
        super().save(*args, **kwargs) """
    
    def save(self, *args, **kwargs):
        self.fecha_pago = self.calcular_fecha_pago()

        # Verifica que fecha_pago no sea None antes de guardar
        if self.fecha_pago is None:
            print("Advertencia: fecha_pago no se pudo calcular.")

        self.estatus_pago = self.calcular_estatus_pago()
        super().save(*args, **kwargs)

    def calcular_total(self):
        """ Suma los importes de todos los documentod relacionados y actualiza el campo total. """
        self.total = sum(detalle.importe for detalle in self.documentos_d.all())
        self.save()

    
    class Meta:  # Corregido "meta" por "Meta"
            verbose_name = "Documento"
            verbose_name_plural = "Documentos"

class CompraDet(ClaseModelo):
     compra = models.ForeignKey(CompraEnc, on_delete=models.CASCADE, related_name='encabezado')
     material = models.ForeignKey(Material, on_delete=models.CASCADE)
     cantidad = models.DecimalField('cantidad:', max_digits=12, decimal_places=3, default=0.000)
     precio_unitario = models.DecimalField('precio unitario:', max_digits=12, decimal_places=2, default=0.00)
     importe = models.DecimalField('Importe',max_digits=10,decimal_places=2,default=0.00)

     def __str__(self):
         return f"{self.material.nombre} - cantidad: {self.cantidad} - precio unitario: {self.precio_unitario}"
     
     def save(self, *args, **kwargs):
        # Convertir cantidad y precio_unitario a Decimal para evitar errores
        self.cantidad = Decimal(self.cantidad)
        self.precio_unitario = Decimal(self.precio_unitario)

        # Calcular el importe
        self.importe = self.cantidad * self.precio_unitario

        # Obtener el valor anterior de importe para ajustar el total si el registro ya existía
        if self.pk:
            compra_det_anterior = CompraDet.objects.get(pk=self.pk)
            # Restar el importe anterior del total de la compra
            self.compra.total -= Decimal(compra_det_anterior.importe)

        # Asegurarse de que el total de la compra también sea Decimal
        self.compra.total = Decimal(self.compra.total) + self.importe
        self.compra.save()

        super(CompraDet, self).save(*args, **kwargs)
        
     def clean(self):
         if self.cantidad < 0:
             raise ValidationError('la cantidad no puede ser negativa.')
         if self.precio_unitario < 0:
             raise ValidationError('el precio unitario no puede ser negativo.')

     def delete(self, *args, **kwargs):
         documento_b = self.documento
         super().delete(*args, **kwargs)  # elimina el documentod
         documento_b.calcular_total()  # recalcula el total en documentob    

     class meta:
         verbose_name = "documento d"
         verbose_name_plural = "documentos d"    



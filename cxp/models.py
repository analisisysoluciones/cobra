from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo
from inv.models import Material
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from django.apps import apps


class Proveedor(ClaseModelo):
    razon_social = models.CharField('Razon social', max_length=120)
    domicilio = models.CharField('Domicilio', max_length=120)
    telefono = models.CharField('Telefono', max_length=45)
    email = models.EmailField('Email')
    experiencia = models.ForeignKey('adm.Simbologia', on_delete=models.CASCADE)

    def obtener_simbologia(self):
        Simbologia = apps.get_model('adm', 'Simbologia')
        return Simbologia.objects.all()
    
    def save(self, *args, **kwargs):
        self.razon_social = self.razon_social.upper()
        self.domicilio = self.domicilio.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.razon_social


class CompraEnc(ClaseModelo):
    tipo = models.ForeignKey('adm.TipoDocumento', on_delete=models.CASCADE, related_name='documentos')
    fecha = models.DateField()
    orden_compra = models.IntegerField('Orden de Compra', blank=True, null=True, default=0)
    folio_documento = models.CharField('Folio Documento', max_length=25, default='S/N')
    inventario = models.BooleanField('inventario:', default=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='documentos')
    total = models.DecimalField('total:', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    archivo_pdf = models.FileField('archivo pdf:', upload_to='documentos/pdfs/', blank=True, null=True)
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.CASCADE, related_name='documentos')
    estado = models.CharField('Estado', default='Pendiente', max_length=15)
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
        pagos_realizados = self.pagos.aggregate(models.Sum('monto'))['monto__sum'] or Decimal('0.00')
        return self.total - pagos_realizados

    def calcular_fecha_pago(self):
        if self.fecha and self.dias_credito is not None:
            try:
                return self.fecha + timedelta(days=int(self.dias_credito))
            except (ValueError, TypeError):
                return self.fecha
        return self.fecha

    def calcular_estatus_pago(self):
        hoy = date.today()
        if self.fecha_pago:
            if hoy > self.fecha_pago:
                return 'vencido'
            elif hoy >= self.fecha_pago - timedelta(days=5):
                return 'proximo_vencer'
        return 'pendiente'

    def save(self, *args, **kwargs):
        self.fecha_pago = self.calcular_fecha_pago()
        self.estatus_pago = self.calcular_estatus_pago()
        super().save(*args, **kwargs)

    def calcular_total(self):
        self.total = sum(detalle.importe for detalle in self.documentos_d.all())
        CompraEnc.objects.filter(pk=self.pk).update(total=self.total)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"


class CompraDet(ClaseModelo):
    compra = models.ForeignKey(CompraEnc, on_delete=models.CASCADE, related_name='documentos_d')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad = models.DecimalField('cantidad:', max_digits=12, decimal_places=3, default=Decimal('0.000'))
    precio_unitario = models.DecimalField('precio unitario:', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    importe = models.DecimalField('Importe', max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.material.nombre} - cantidad: {self.cantidad} - precio unitario: {self.precio_unitario}"

    def save(self, *args, **kwargs):
        self.cantidad = Decimal(self.cantidad)
        self.precio_unitario = Decimal(self.precio_unitario)
        self.importe = self.cantidad * self.precio_unitario

        super().save(*args, **kwargs)
        self.compra.calcular_total()

    def clean(self):
        if self.cantidad < 0:
            raise ValidationError('La cantidad no puede ser negativa.')
        if self.precio_unitario < 0:
            raise ValidationError('El precio unitario no puede ser negativo.')

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.compra.calcular_total()

    class Meta:
        verbose_name = "documento d"
        verbose_name_plural = "documentos d"

from django.db import models
from bases.models import ClaseModelo
import uuid
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone

# Create your models here.

class Categoria(ClaseModelo):
    descripcion = models.CharField(
        max_length=100,
        help_text='Descripcion de la categoria',
        unique=True
    )

    def __str__(self):
        return "{}".format(self.descripcion)
    
    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Categorias'
        verbose_name = 'Categoria'

class Unidad(models.Model):
    clave = models.CharField('Unidad:',max_length=15,unique=True)
    descripcion = models.CharField('Descripcion:',max_length=60)

    def __str__(self):
        return f"{self.clave}, {self.descripcion}"
    
    def save(self):
        self.descripcion = self.descripcion.upper()
        self.clave = self.clave.upper()
        super(Unidad, self).save()

    class Meta:
        verbose_name = 'Unidad'
        verbose_name_plural = 'Undiades'

class Material(ClaseModelo):
    clave = models.CharField('clave', max_length=25, unique=True)
    descripcion = models.CharField('Descripcion:',max_length=120, blank=False, null=False)
    existencia = models.DecimalField('Existencia:', max_digits=12,decimal_places=3,default=0.000)
    minimo = models.DecimalField('Minimo:', max_digits=12,decimal_places=3,default=0.000)
    maximo = models.DecimalField('Maximo:', max_digits=12,decimal_places=3,default=0.000)
    unidad_medida = models.ForeignKey(Unidad, on_delete=models.CASCADE,null=True)
    TIPO_INSUMO = (
        ('MATERIAL','Material'),
        ('MANO_OBRA','Mano de Obra'),
        ('EQUIPO','Equipo'),
        ('HERRAMIENTA','Herramienta'),
    )

    tipo_insumo = models.CharField(
        'Tipo insumo',
        max_length=20,
        choices=TIPO_INSUMO,
        default='MATERIAL'
    )


    def __str__(self):
        return str(self.id)
    
    def save(self):
        self.descripcion = self.descripcion.upper()
        self.clave = self.clave.upper()
        super(Material, self).save()


# tipo_gastos=[
#     ('Fijo','Fijo'),
#     ('Variable','Variable'),
#     ('Administrativo','Adminitrativo'),
#     ('Directo','Directo'),
#     ('Indirecto','Indirecto'),
#     ('Financiero','Financiero'),
#     ('Esencial','Esencial'),
#     ('Discrecional','Discrecional'),
# ]

# class Conceptos(models.Model):
#     descripcion=models.CharField('Descripcion',max_length=120)
#     tipo = models.CharField('Tipo',choices=tipo_gastos,default='Fijo')
    

# Modelo para requisiciones
class Requisicion(models.Model):
    folio = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    solicitante = models.ForeignKey('nomina.Empleado', on_delete=models.CASCADE)
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.CASCADE,null=True,blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    estatus = models.CharField(
        max_length=20,
        choices=[('PENDIENTE', 'Pendiente'), ('ENTREGADA', 'Entregada'), ('CANCELADA', 'Cancelada')],
        default='PENDIENTE'
    )
    comentarios = models.TextField(blank=True)

    def __str__(self):
        return f"Requisición {self.folio}"

    def calcular_totales(self):
        # Similar a calcular_total en CompraEnc, pero para cantidades
        self.total_solicitada = sum(item.cantidad_solicitada for item in self.items.all())
        self.total_entregada = sum(item.cantidad_entregada for item in self.items.all())
        # No se guarda en el modelo, pero se puede usar en vistas

class ItemRequisicion(models.Model):
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    cantidad_solicitada = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.000'))]
    )
    cantidad_entregada = models.DecimalField(
        max_digits=12, decimal_places=3,
        default=0,
        validators=[MinValueValidator(Decimal('0.000'))]
    )
    verificado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.material.descripcion} - Solicitado: {self.cantidad_solicitada} - Entregado: {self.cantidad_entregada}"

    def clean(self):
        if self.cantidad_solicitada < 0:
            raise ValidationError('La cantidad solicitada no puede ser negativa.')
        if self.cantidad_entregada < 0:
            raise ValidationError('La cantidad entregada no puede ser negativa.')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.requisicion.calcular_totales()

class Firma(models.Model):
    requisicion = models.ForeignKey(Requisicion, on_delete=models.CASCADE)
    empleado = models.ForeignKey('nomina.Empleado', on_delete=models.CASCADE)
    fecha_firma = models.DateTimeField(auto_now_add=True)
    imagen_firma = models.ImageField(upload_to='firmas/', blank=True, null=True)
    comentarios = models.TextField(blank=True)

    def __str__(self):
        return f"Firma de {self.empleado.nombre} para {self.requisicion}"
    

    # operacion/models/salida_almacen.py  (sugiero app operacion)


class SalidaAlmacen(ClaseModelo):
    fecha = models.DateField(default=timezone.now)

    proyecto = models.ForeignKey(
        'adm.Proyecto',
        on_delete=models.PROTECT,
        related_name='salidas_almacen'
    )

    equipo = models.ForeignKey(
        'adm.Equipo',          # ← TU MODELO EXISTENTE
        on_delete=models.PROTECT,
        related_name='salidas_almacen'
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='salidas_equipo'
    )

    requisicion = models.ForeignKey(
        Requisicion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='salidas_almacen'
    )

    compra = models.ForeignKey(
        'cxp.CompraEnc',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='salidas_almacen'
    )

    observaciones = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Salida de almacén'
        verbose_name_plural = 'Salidas de almacén'
        db_table = 'op_salida_almacen'

    def __str__(self):
        return f"Salida #{self.id} - {self.equipo.descripcion}"


# operacion/models/salida_almacen_detalle.py
from django.db import models
from django.utils import timezone


class SalidaAlmacenD(ClaseModelo):
    salida = models.ForeignKey(
        SalidaAlmacen,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='salidas_almacen'
    )

    cantidad = models.DecimalField(
        'Cantidad',
        max_digits=12,
        decimal_places=3
    )

    unidad = models.CharField(
        'Unidad',
        max_length=20,
        default='PZA'
    )

    costo_unitario = models.DecimalField(
        'Costo unitario',
        max_digits=14,
        decimal_places=4,
        default=0
    )

    class Meta:
        verbose_name = 'Detalle salida de almacén'
        verbose_name_plural = 'Detalles salida de almacén'
        db_table = 'op_salida_almacen_d'
        indexes = [
            models.Index(fields=['material']),
        ]

    def __str__(self):
        return f"{self.material} x {self.cantidad}"

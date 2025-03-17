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


# Create your models here.

escoge_tipo = [
    ('Padre','Padre'),
    ('Hijo','Hijo')
]

t_cuenta = [
    ('General','General'),
    ('Proyecto','Proyecto')
]


class Simbologia(models.Model):
    origen = models.IntegerField('Familia',default=0)
    clave = models.IntegerField('Consecutivo',default=0)
    descripcion = models.CharField('Descripcion',max_length=120,blank=True)
    abreviatura = models.CharField('Abreviatura',max_length=15,blank=True)
    estatus = models.BooleanField(default=True)       
    tipo = models.CharField('Tipo',max_length=5,choices=escoge_tipo,default='Hijo')
    
    def __str__(self):
        return str(self.origen)+ " " + self.descripcion
    
    
    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.abreviatura = self.abreviatura.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Simbología"
        verbose_name_plural = "Simbologías"
       
        

class Proveedor(ClaseModelo):
    razon_social = models.CharField('Razon social',max_length=120,blank=False,null=False)
    domicilio = models.CharField('Domicilio',max_length=120,blank=False,null=False)
    telefono = models.CharField('Telefono',max_length=45)
    email = models.EmailField('Email')
    experiencia = models.ForeignKey(Simbologia,on_delete=models.CASCADE)
    
    def save(self):
        self.razon_social = self.razon_social.upper()
        self.domicilio = self.domicilio.upper()
        super(Proveedor, self).save()
    
    def __str__(self):
        return self.razon_social
    

class Banco(models.Model):
    nombre = models.CharField('Nombre del Banco', max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    def save(self):
        self.nombre = self.nombre.upper()
        super(Banco, self).save()

    class Meta:
        verbose_name_plural = "Bancos"
        verbose_name = "Banco"
        



class Cuenta(ClaseModelo):
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, related_name='cuentas')
    cuenta = models.CharField('Número de Cuenta', max_length=20, unique=True)
    clabe = models.CharField('CLABE', max_length=18, unique=True)
    saldo_inicial = models.DecimalField('Saldo Inicial', max_digits=12, decimal_places=2)
    saldo_actual = models.DecimalField('Saldo Actual', max_digits=12, decimal_places=2)
    tipo_cuenta = models.CharField('Tipo',choices=t_cuenta,default='Proyecto',null=True,blank=True)

    def __str__(self):
        return f"{self.banco.nombre} - {self.cuenta}"

    class Meta:
        verbose_name_plural = "Cuentas"
        verbose_name = "Cuenta"
        ordering = ['id']

movimiento_choice=[
    ('Abono','Abono'),
    ('Cargo','Cargo')
]

class Residente(ClaseModelo):
    nombre = models.CharField('Nombre:', max_length=120, blank=False, null=False, unique=True)

    def __str__(self):
        return self.nombre.upper()
    
    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super().save(*args, **kwargs)


class TipoDocumento(models.Model):
    tipo = models.CharField('Documento:', max_length=25, blank=False, null=False, unique=True)
    movimiento = models.CharField('Tipo:', max_length=12, choices=movimiento_choice)

    def __str__(self):
        return self.tipo.upper()
    
    def save(self, *args, **kwargs):
        self.tipo = self.tipo.upper()
        super().save(*args, **kwargs)


class Proyecto(ClaseModelo):
    nombre = models.CharField('Nombre:', max_length=120, blank=False, null=False, default='')
    ubicacion = models.CharField('Ubicación:', max_length=120)
    latitud = models.DecimalField('Latitud:', max_digits=9, decimal_places=6)
    longitud = models.DecimalField('Longitud:', max_digits=9, decimal_places=6)
    residente = models.ForeignKey(Residente, on_delete=models.CASCADE, related_name='proyectos')
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name='proyectos')
    mapa = models.FileField('Mapa del Proyecto', upload_to='mapas/', blank=True, null=True)  # Para PDF o imágenes
    
    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.ubicacion = self.ubicacion.upper()
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"


class CompraEnc(ClaseModelo):
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.CASCADE, related_name='documentos')
    fecha = models.DateField()
    orden_compra = models.IntegerField('Orden de Compra',blank=True,null=True,default=0)
    folio_documento = models.CharField('Folio Documento',max_length=25,blank=False,null=False,default='S/N')
    inventario = models.BooleanField('inventario:', default=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='documentos')
    total = models.DecimalField('total:', max_digits=12, decimal_places=2, default=0.00)
    archivo_pdf = models.FileField('archivo pdf:', upload_to='documentos/pdfs/', blank=True, null=True)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='documentos')
    estado = models.CharField('Estado',default='Pendiente',max_length=15)
    dias_credito = models.PositiveIntegerField('Días de Crédito', default=0)
    fecha_pago = models.DateField('Fecha de Pago', blank=True, null=True)

    ESTATUS_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('proximo_vencer', 'Próximo a vencer'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
    ]
    estatus_pago = models.CharField('Estatus de Pago', max_length=15, choices=ESTATUS_PAGO_CHOICES, default='pendiente')

    def calcular_fecha_pago(self):
        """ Calcula la fecha de pago sumando los días de crédito a la fecha de la compra """
        if self.dias_credito and self.fecha:
            return self.fecha + timedelta(days=self.dias_credito)
        return None

    def calcular_estatus_pago(self):
        """ Determina el estado de pago basado en la fecha actual """
        hoy = date.today()
        if self.fecha_pago:
            if hoy > self.fecha_pago and self.estatus_pago == 'pendiente':
                return 'vencido'
            elif hoy >= self.fecha_pago - timedelta(days=5) and self.estatus_pago == 'pendiente':
                return 'proximo_vencer'
        return self.estatus_pago

    def calcular_total(self):
        """ Suma los importes de todos los documentod relacionados y actualiza el campo total. """
        self.total = sum(detalle.importe for detalle in self.documentos_d.all())
        self.save()

    def save(self, *args, **kwargs):
        if not self.fecha_pago:
            self.fecha_pago = self.calcular_fecha_pago()
        self.estatus_pago = self.calcular_estatus_pago()
        super().save(*args, **kwargs)

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



        
class Equipo(ClaseModelo):
    identificador = models.IntegerField('Identificador',unique=True,default=0)
    descripcion = models.CharField('Descripcion',max_length=60,blank=False,null=False,default='Unidad')
    modelo=models.IntegerField('Modelo',blank=False,null=False,default=0)
    placas=models.CharField('Placas',max_length=10,blank=True,null=True,default='S/P')
        
    def __str__(self):
        return self.descripcion
        
    def save(self):
        self.descripcion = self.descripcion.upper()
        self.placas = self.placas.upper()
        super(Equipo, self).save()
    
    class Meta:
        verbose_name = 'Maquinaria y equipo'
        verbose_name_plural = 'Maquinarias y equipos'


        


class RegistroCuenta(ClaseModelo):  # Cambié a `models.Model`
    fecha_movimiento = models.DateField()
    concepto = models.CharField('Concepto', max_length=120, blank=False, null=False, default='Concepto por comprobar')
    cantidad = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0.00)
    cuenta = models.ForeignKey('Cuenta', on_delete=models.CASCADE)
    folio_documento = models.CharField('Folio documento', max_length=15, blank=True, null=True, default='S/F')
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE, null=True, blank=True)
    reposicion_flujo = models.BooleanField('Reposicion de caja', default=True)
    
    def __str__(self):
        return f"{self.fecha_movimiento} {self.concepto} {self.cantidad}"
    
    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_update = self.pk is not None

        if is_update:
            original = RegistroCuenta.objects.get(pk=self.pk)
            if original.cantidad != self.cantidad:
                if original.cuenta:
                    original.cuenta.saldo_actual += original.cantidad  # Revertir el antiguo
                if self.cuenta:
                    self.cuenta.saldo_actual -= self.cantidad  # Aplicar el nuevo
        else:
            if self.reposicion_flujo:
                self.cuenta.saldo_actual += self.cantidad
            else:
                self.cuenta.saldo_actual -= self.cantidad

        super(RegistroCuenta, self).save(*args, **kwargs)

        if self.cuenta:
            self.cuenta.save()


    
    class Meta:
        verbose_name = 'Registro'
        verbose_name_plural = 'Registros'




    
class Bitacora(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="bitacoras")
    fecha = models.DateField(auto_now_add=True)
    actividad = models.TextField()
    personal_involucrado = models.CharField(max_length=255)
    maquinaria_utilizada = models.CharField(max_length=255, blank=True, null=True)
    avance = models.TextField(blank=True, null=True)
    material_entregado = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Bitácora del {self.fecha} para {self.proyecto.nombre}"



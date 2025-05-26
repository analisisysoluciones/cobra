from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo
from cxp.models import CompraEnc
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
import re
from django.utils import timezone
from datetime import date, timedelta
from django.apps import apps





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


class RegistroCuenta(ClaseModelo):
    fecha_movimiento = models.DateField()
    concepto = models.CharField('Concepto', max_length=120, blank=False, null=False, default='Concepto por comprobar')
    cantidad = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0.00)
    cuenta = models.ForeignKey('Cuenta', on_delete=models.CASCADE)
    folio_documento = models.CharField('Folio documento', max_length=15, blank=True, null=True, default='')
    reposicion_flujo = models.BooleanField('Reposición de caja', default=True)  # True = Abono, False = Retiro

    def __str__(self):
        return f"{self.fecha_movimiento} {self.concepto} {self.cantidad}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_update = self.pk is not None

            if is_update:
                original = RegistroCuenta.objects.get(pk=self.pk)
                diferencia = self.cantidad - original.cantidad

                if original.reposicion_flujo:
                    original.cuenta.saldo_actual -= original.cantidad  # Revertimos el saldo anterior
                else:
                    original.cuenta.saldo_actual += original.cantidad  # Revertimos el saldo anterior

            # Aplicamos el nuevo saldo
            if self.reposicion_flujo:
                self.cuenta.saldo_actual += self.cantidad  # Es un abono
                movimiento_tipo = "abono"
            else:
                self.cuenta.saldo_actual -= self.cantidad  # Es un retiro
                movimiento_tipo = "retiro"

            super(RegistroCuenta, self).save(*args, **kwargs)
            self.cuenta.save()

            # Registrar en MovimientoCuenta
            MovimientoCuenta.objects.create(
                cuenta=self.cuenta,
                fecha=self.fecha_movimiento,
                descripcion=self.concepto,
                cargo=self.cantidad if not self.reposicion_flujo else 0,
                abono=self.cantidad if self.reposicion_flujo else 0,
                saldo=self.cuenta.saldo_actual
            )

    class Meta:
        verbose_name = 'Registro'
        verbose_name_plural = 'Registros'


class TipoPago(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Pago(models.Model):
    # CompraEnc = apps.get_model('cxp', 'CompraEnc')
    compra = models.ForeignKey(CompraEnc, on_delete=models.CASCADE, related_name='pagos')
    tipo_pago = models.ForeignKey(TipoPago, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    cuenta_bancaria = models.ForeignKey(Cuenta, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Nuevo campo


    class Meta:
        unique_together = ('compra', 'tipo_pago', 'monto')  # Evita pagos idénticos

    def get_compra_enc_model(self):
        return apps.get_model('cxp', 'CompraEnc')

    def save(self, *args, **kwargs):
        saldo_pendiente = self.compra.total - sum(p.monto for p in self.compra.pagos.all())

        if self.monto > saldo_pendiente:
            raise ValidationError("El pago excede el saldo pendiente")

        super().save(*args, **kwargs)

        # ✅ Si hay cuenta bancaria, registrar movimiento y actualizar saldo
        if self.cuenta_bancaria:
            self.cuenta_bancaria.saldo_actual -= self.monto
            self.cuenta_bancaria.save()

            # ✅ Guardar el pago como movimiento en la cuenta bancaria
            MovimientoCuenta.objects.create(
                cuenta=self.cuenta_bancaria,
                fecha=self.fecha,
                descripcion=f"Pago a {self.compra.proveedor.razon_social}",
                cargo=self.monto,
                abono=0.00,  # Salida de dinero
                saldo=self.cuenta_bancaria.saldo_actual
            )

    def __str__(self):
        return f"Pago de {self.monto} a {self.compra.proveedor.razon_social}"
    

class MovimientoCuenta(models.Model):
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255)
    cargo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Salida de dinero
    abono = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Entrada de dinero
    saldo = models.DecimalField(max_digits=10, decimal_places=2)  # Saldo después del movimiento

    def __str__(self):
        return f"{self.fecha.date()} - {self.descripcion} - Saldo: {self.saldo}"
    
# class CostoProyecto(models.Model):
#     proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
#     fecha = models.DateField(auto_now_add=True)
#     simbologia = models.ForeignObject(Simbologia, on_delete=models.PROTECT, verbose_name='Tipo de costo')
#     descripcion = models.CharField(max_length=255)
#     monto = models.DecimalField(max_digits=12, decimal_places=2)
#     movimiento = models.OneToOneField(MovimientoCuenta, null=True, blank=True, on_delete=models.SET_NULL)

#     def __str__(self):
#        return f"{self.fecha.date()} - {self.descripcion} - ${self.monto}"

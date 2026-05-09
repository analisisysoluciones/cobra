from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo, Folios
from cxp.models import CompraEnc, Proveedor
from django.core.exceptions import ValidationError
from django.db import transaction, models
from decimal import Decimal
import re
from django.utils import timezone
from datetime import date, timedelta
from django.apps import apps
from django.db.models import Sum, F, Q, UniqueConstraint
from django.core.validators import FileExtensionValidator
from django.contrib.postgres.indexes import GinIndex
from django.conf import settings

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
    presupuesto = models.DecimalField('Presupuesto asignado', max_digits=12, decimal_places=2, default=0)


    @property
    def total_usado(self):
        return self.cuenta.movimientos.aggregate(total=Sum('importe'))['total'] or 0

    @property
    def avance_presupuesto(self):
        if self.presupuesto > 0:
            return round((self.total_usado / self.presupuesto) * 100, 2)
        return 0

    
    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.ubicacion = self.ubicacion.upper()
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"

class TipoEquipo(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre     


class Equipo(ClaseModelo):
    identificador = models.IntegerField('Identificador',unique=True,default=0)
    descripcion = models.CharField('Descripcion',max_length=60,blank=False,null=False,default='Unidad')
    modelo=models.CharField('Modelo',max_length=20,blank=False,null=False,default=0)
    placas=models.CharField('Placas',max_length=10,blank=True,null=True,default='S/P')
    tipo_equipo = models.ForeignKey(
        TipoEquipo,
        on_delete=models.PROTECT, null=True, blank=True
    )

    # 👇 clave para lo que descubriste hoy
    TIPO_CONTROL = (
        ("HORAS", "Por horas (hodómetro)"),
        ("KM", "Por kilometraje"),
        ("GPS", "Por GPS"),
    )
    tipo_control = models.CharField(max_length=10, choices=TIPO_CONTROL, null=True, blank=True, default="KM")

    TIPO_EQUIPO = [
    ("PESADO", "Pesado"),
    ("LIGERO", "Ligero"),
    ("VEHICULO", "Vehículo"),
    ]

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_EQUIPO,
        default="LIGERO"
    )

    def __str__(self):
        return f"{self.descripcion} ({self.placas})"
        
            
    def save(self, *args, **kwargs):
        if self.modelo:
            self.modelo = self.modelo.upper().strip()
        self.descripcion = self.descripcion.upper()
        self.placas = self.placas.upper()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Maquinaria y equipo'
        verbose_name_plural = 'Maquinarias y equipos'

    
class Bitacora(models.Model):
    proyecto = models.ForeignKey(
        'Proyecto',
        on_delete=models.CASCADE,
        related_name="bitacoras"
    )
    fecha = models.DateField()
    contenido = models.TextField(
        help_text="Ingrese el contenido de la bitácora en texto libre (puede incluir HTML).",blank=True,null=True
    )
    documento = models.FileField(
        upload_to='bitacoras/',
        blank=True,
        null=True,
        verbose_name="Documento PDF"
    )

    def __str__(self):
        return f"Bitácora del {self.fecha} - {self.proyecto.nombre}"


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




class DocumentoGeneral(models.Model):
    TIPOS = (
        ('cotizacion', 'Cotización'),
        ('registro', 'Registro'),
        ('bitacora', 'Bitácora'),
        ('otro', 'Otro'),
    )

    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.CharField(max_length=255)
    archivo = models.FileField(upload_to='documentos_generales/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descripcion}"



class CargaCombustible(ClaseModelo):
    COMBUSTIBLE_CHOICES = (
        ('gasolina', 'Gasolina'),
        ('diesel', 'Diésel'),
    )

    equipo = models.ForeignKey(
        'Equipo',
        on_delete=models.CASCADE,
        related_name='cargas_combustible'
    )
    fecha_carga = models.DateField()
    tipo_combustible = models.CharField(
        max_length=10,
        choices=COMBUSTIBLE_CHOICES
    )
    cantidad_litros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Cantidad en litros'
    )
    costo_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Costo total de esta carga'
    )
    odometro = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Lectura del odómetro si aplica'
    )
    observaciones = models.TextField(
        blank=True,
        null=True
    )
    operador = models.CharField(max_length=80,null=True,blank=True)

    operador_fk = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,related_name='cargas_operadas')

    hora = models.TimeField(null=True, blank=True)
    folio = models.CharField(
        "Folio del ticket",
        max_length=30,
        null=True,
        blank=True
    )
    proyecto = models.ForeignKey(Proyecto,on_delete=models.CASCADE, null=True, blank=True)
    foto = models.ImageField(
        upload_to='combustible/',
        blank=True,
        null=True
    )
    gasolinera = models.CharField(max_length=120, blank=True, null=True)

    tanque_lleno = models.BooleanField(default=False)

    precio_litro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if not self.pk:  # Solo al crear (no al editar)
            # Hora actual en zona horaria de México
            now_mx = timezone.now().astimezone(timezone.get_current_timezone())
            self.folio = self.folio.strip().upper()
            self.hora = now_mx.time()  # solo la parte de hora:minuto:segundo

        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.get_tipo_combustible_display()} - {self.equipo} - {self.fecha_carga}"
    
    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['equipo', 'fecha_carga', 'folio'],
                condition=Q(folio__isnull=False),
                name='unique_folio_por_equipo_fecha'
            )
        ]
        ordering = ['-fecha_carga', '-id']
        indexes = [

            # Índices simples (altamente recomendados)
            models.Index(fields=['fecha_carga']),
            models.Index(fields=['equipo']),
            models.Index(fields=['proyecto']),
            models.Index(fields=['tipo_combustible']),

            # Índices compuestos para reportes rápidos
            models.Index(fields=['fecha_carga', 'equipo']),
            models.Index(fields=['proyecto', 'fecha_carga']),

            
        ]
    
    


class ReporteEquipo(ClaseModelo):
    fecha = models.DateField(null=True,blank=True)
    Proyecto = models.ForeignKey(Proyecto,on_delete=models.SET_NULL, null=True, blank=True)
    equipo = models.ForeignKey(Equipo,on_delete=models.SET_NULL, null=True, blank=True)
    operador = models.CharField('Operador',max_length=80,blank=True,null=True)
    actividad = models.CharField('Actividad',max_length=220,null=True,blank=True)
    horas = models.CharField('Horas',max_length=10,null=True,blank=True)
    diesel_carga = models.CharField('Diesel Cargado',max_length=15,null=True,blank=True)
    diesel_resta = models.CharField('Diesel Restante',max_length=15,null=True,blank=True)
    fallas = models.CharField('Fallas',max_length=120,blank=True,null=True)
    observa = models.CharField('Observaciones',max_length=220,null=True,blank=True)

    def __str__(self):
        return f"{self.equipo} - {self.operador}"
    
    class Meta:
        verbose_name_plural = "Reportes de Equipo"
    

class PagoIndirecto(ClaseModelo):
    ESTATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('AFECTADO', 'Afectado'),
    ]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="pagos_indirectos_proyecto")
    proveedor = models.ForeignKey('cxp.Proveedor', on_delete=models.CASCADE, related_name="pagos_indirectos_proveedor")
    documento = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_indirectos_documento")
    folio_documento = models.CharField('Folio', max_length=20, blank=True)
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField(default=timezone.now)
    tipo_pago = models.ForeignKey(TipoPago, on_delete=models.PROTECT, related_name="pagos_indirectos_tipopago")
    comprobante = models.FileField(
        upload_to='comprobantes/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, default='PENDIENTE')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Permitir guardar si se llama desde afectar_pago o si es un nuevo registro
            allow_afectado = kwargs.pop('allow_afectado', False)
            if self.pk and self.estatus.upper() == 'AFECTADO' and not allow_afectado:
                raise ValueError("No se puede editar un pago en estatus AFECTADO.")
            
            # Asignar folio si es "s/n" o está vacío y documento no es nulo
            if (not self.folio_documento or self.folio_documento.lower() in ['s/n', 'sn']) and self.documento:
                folio_registro, created = Folios.objects.get_or_create(
                    tipo_documento=self.documento.tipo,
                    anio=timezone.now().year,
                    defaults={'consecutivo': 0}
                )
                self.folio_documento = folio_registro.next_consecutivo()
            
            super().save(*args, **kwargs)

    def afectar_pago(self):
        """Confirma el pago, deduce saldos y registra en MovimientoCuenta."""
        with transaction.atomic():
            if self.estatus.upper() == 'AFECTADO':
                raise ValueError("El pago ya está afectado.")
            if not hasattr(self.proyecto, 'cuenta') or self.proyecto.cuenta is None:
                raise ValueError("El proyecto no tiene una cuenta asociada.")
            if self.proyecto.presupuesto < self.monto or self.proyecto.cuenta.saldo_actual < self.monto:
                raise ValueError("Saldo insuficiente en el proyecto o la cuenta.")
            
            # Deducir saldos
            self.proyecto.presupuesto -= self.monto
            self.proyecto.cuenta.saldo_actual -= self.monto
            self.proyecto.save()
            self.proyecto.cuenta.save()

            # Registrar movimiento
            MovimientoCuenta.objects.create(
                cuenta=self.proyecto.cuenta,
                fecha=self.fecha,
                descripcion=f"Gasto indirecto: {self.descripcion} (Folio: {self.folio_documento or 'Sin folio'})",
                cargo=self.monto,
                abono=0,
                saldo=self.proyecto.cuenta.saldo_actual,
            )

            # Cambiar estatus y guardar con permiso especial
            self.estatus = 'AFECTADO'
            self.save(allow_afectado=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.descripcion} - ${self.monto} ({self.get_estatus_display()}) - Folio: {self.folio_documento or 'Sin folio'}"


# operacion/models/orden_servicio.py


class OrdenServicio(ClaseModelo):

    TIPO_SERVICIO = (
        ('PRE', 'Preventivo'),
        ('COR', 'Correctivo'),
    )

    ESTATUS = (
        ('ABIERTA', 'Abierta'),
        ('AUTORIZADA', 'Autorizada'),
        ('PROCESO', 'En proceso'),
        ('CERRADA', 'Cerrada'),
        ('CANCELADA', 'Cancelada'),
    )

    fecha = models.DateField(default=timezone.now)

    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.PROTECT,
        related_name='ordenes_servicio'
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='ordenes_servicio'
    )

    tipo_servicio = models.CharField(
        max_length=3,
        choices=TIPO_SERVICIO,
        default='COR'
    )

    descripcion_falla = models.TextField()

    estatus = models.CharField(
        max_length=15,
        choices=ESTATUS,
        default='ABIERTA'
    )
    proyecto = models.ForeignKey(
        'adm.Proyecto',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    costo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    responsable = models.CharField(
        max_length=200,
        blank=True
    )
    estado = models.CharField(
        max_length=100,
        blank=True
    )

    observaciones = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Orden de servicio'
        verbose_name_plural = 'Órdenes de servicio'
        db_table = 'op_orden_servicio'
        ordering = ['-fecha']

    def __str__(self):
        return f"OS-{self.id} | {self.equipo}"



class MantenimientoEquipo(models.Model):
    equipo = models.ForeignKey(
        'Equipo',
        on_delete=models.CASCADE,
        related_name='mantenimientos'
    )

    proyecto = models.ForeignKey(
        'Proyecto',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mantenimientos'
    )

    fecha = models.DateField()

    TIPO_CHOICES = [
        ('PREVENTIVO', 'Preventivo'),
        ('CORRECTIVO', 'Correctivo'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    descripcion = models.TextField()

    proveedor = models.CharField(max_length=200, blank=True)

    costo = models.DecimalField(max_digits=12, decimal_places=2)

    proximo_cambio = models.DateField(null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.equipo} - {self.tipo} - {self.fecha}"


# models.py
class ActividadEquipo(models.Model):

    nombre = models.CharField(max_length=100)

    TIPO = (
        ("PRODUCTIVO", "Productivo"),
        ("SOPORTE", "Soporte"),
        ("MUERTO", "Tiempo muerto"),
    )
    tipo = models.CharField(max_length=20, choices=TIPO)

    # 👇 relación inteligente
    tipos_equipo = models.ManyToManyField(TipoEquipo)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class ReporteEquipoPDA(models.Model):
    equipo = models.ForeignKey('Equipo', on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    inicio = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(null=True, blank=True)

    
    foto_inicio = models.ImageField(upload_to='reportes/inicio/', null=True, blank=True)
    foto_fin = models.ImageField(upload_to='reportes/fin/', null=True, blank=True)

    latitud_inicio = models.FloatField(null=True, blank=True)
    longitud_inicio = models.FloatField(null=True, blank=True)

    latitud_fin = models.FloatField(null=True, blank=True)
    longitud_fin = models.FloatField(null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    estatus = models.CharField(
        max_length=10,
        choices=[('ABIERTA','ABIERTA'), ('CERRADA','CERRADA')],
        default='ABIERTA'
    )

    def __str__(self):
        return f"{self.equipo} - {self.usuario}"

    class Meta:
        indexes = [
            models.Index(fields=['usuario', 'fin']),
            models.Index(fields=['equipo', 'fin']),
        ]

        constraints = [
            UniqueConstraint(
                fields=["usuario"],
                condition=Q(estatus="ACTIVA"),
                name="unique_jornada_activa_por_usuario"
            )
        ]

    @property
    def horas(self):
        return sum(d.horas for d in self.detalles.all())


class ReporteEquipoDetalle(models.Model):

    reporte = models.ForeignKey(ReporteEquipoPDA, on_delete=models.CASCADE, related_name="detalles")

    actividad = models.ForeignKey(ActividadEquipo, on_delete=models.PROTECT)

    inicio = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(null=True, blank=True)

    horas = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    observaciones = models.TextField(null=True, blank=True)

    usuario = models.ForeignKey(User, on_delete=models.PROTECT)

    creado = models.DateTimeField(auto_now_add=True)

    proyecto = models.ForeignKey(
        'adm.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    editado_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    editado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['reporte', 'inicio']),
        ]

    
    def save(self, *args, **kwargs):

        if self.inicio and self.fin:
            delta = self.fin - self.inicio
            self.horas = round(delta.total_seconds() / 3600, 2)
        else:
            self.horas = Decimal("0.00")

        super().save(*args, **kwargs)

    


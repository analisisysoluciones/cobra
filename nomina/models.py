from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo, Folios
from adm.models import Cuenta
from inv.models import Material
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
from decimal import Decimal
from django.db.models import Sum
import re
from django.utils import timezone
from datetime import date, timedelta



class PerfilPuesto(models.Model):
    CATEGORIAS_PUESTO = [
        ("BASICO", "Mano de obra básica"),
        ("OFICIAL", "Oficial"),
        ("TECNICO", "Técnico especializado"),
        ("SUPERVISION", "Supervisión"),
        ("ADMIN", "Administración"),
    ]
    nombre = models.CharField(max_length=100)
    sueldo_min = models.DecimalField(max_digits=10, decimal_places=2)
    sueldo_max = models.DecimalField(max_digits=10, decimal_places=2)
    TIPO_PAGO = (
        ('FIJO', 'Fijo'),
        ('DESTAJO', 'Destajo')
    )
    tipo_pago = models.CharField(max_length=10, choices=TIPO_PAGO, null=True, blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_PUESTO)
    activo = models.BooleanField(default=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} (${self.sueldo_min} - ${self.sueldo_max})"



# Create your models here.
class Empleado(ClaseModelo):
    codigo = models.IntegerField('Codigo',default=0,blank=False,null=False,unique=True,editable=False)
    curp = models.CharField('Curp',max_length=18,blank=False,null=False,unique=True)
    rfc  = models.CharField('Rfc',max_length=13,null=False,blank=False,default='')
    nombre = models.CharField('Nombre',max_length=120,blank=False,null=False,default='')
    ingreso = models.DateField('Ingreso',blank=False,null=False)
    sueldo_diario = models.DecimalField('Sueldo diario',max_digits=10,decimal_places=2,default=0.00)
    compensacion = models.DecimalField('Compensación',decimal_places=2,max_digits=10,default=0.00,blank=True,null=True)
    perfil = models.ForeignKey(PerfilPuesto, on_delete=models.PROTECT, null=True, blank=True)
    tipo_pago = models.CharField(max_length=10, editable=False, null=True, blank=True)
    def años_servicio(self):
        """Calcula los años de servicio del empleado"""
        today = date.today()
        return today.year - self.ingreso.year - ((today.month, today.day) < (self.ingreso.month, self.ingreso.day))

    def dias_vacaciones(self):
        """Retorna la cantidad de días de vacaciones correspondientes según los años de servicio"""
        años = self.años_servicio()
        if años == 1:
            return 12
        elif años == 2:
            return 14
        elif años == 3:
            return 16
        elif años == 4:
            return 18
        elif años == 5:
            return 20
        elif 6 <= años <= 10:
            return 22
        elif 11 <= años <= 15:
            return 24
        elif 16 <= años <= 20:
            return 26
        elif 21 <= años <= 25:
            return 28
        elif 26 <= años <= 30:
            return 30
        elif años >= 31:
            return 32
        return 0  # Si el empleado tiene menos de un año, no le corresponden vacaciones aún

    def asignar_folio_empleado(self):
        """Obtiene el siguiente folio para empleado desde bases_folios"""
        with transaction.atomic():
            folio, creado = Folios.objects.select_for_update().get_or_create(
                tipo_documento="EMPLEADO",
                defaults={"ultimo": 0}
            )
            folio.consecutivo += 1
            folio.save()
            return folio.consecutivo

    def save(self, *args, **kwargs):

    # Asignar folio automático
        if not self.codigo or self.codigo == 0:
            self.codigo = self.asignar_folio_empleado()

        # Uppercase
        self.curp = self.curp.upper()
        self.rfc = self.rfc.upper()
        self.nombre = self.nombre.upper()
        if self.perfil:
            self.sueldo_diario = self.perfil.sueldo_max
            self.tipo_pago = self.perfil.tipo_pago
        

        super().save(*args, **kwargs)

    

        
    def __str__(self):
        perfil = self.perfil.nombre if self.perfil else "Sin perfil"
        return f"{self.nombre} ({perfil})"
        
    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'


class EmpleadoArchivo(models.Model):    
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name='archivos')
    nombre = models.CharField('Tipo de archivo', max_length=20)
    archivo = models.FileField('Archivo', upload_to='empleados_archivos/')
    fecha_subida = models.DateTimeField(auto_now_add=True)


    def clean(self):
        # Solo ejecutar la validación si ya tiene empleado asignado
        if self.empleado_id:  # ✅ Verifica si ya tiene un empleado asignado
            cantidad = EmpleadoArchivo.objects.filter(empleado=self.empleado).count()
            if cantidad >= 5:  # Ejemplo: solo permite 5 archivos por empleado
                raise ValidationError("Este empleado ya tiene el máximo permitido de archivos.")
            
    def save(self, *args, **kwargs):
        self.full_clean()  # Llama a clean() para validar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.empleado.nombre} - {self.nombre}"

    
class Asistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    

    def __str__(self):
        return f"{self.empleado.nombre} - {self.fecha}"
    
    def es_trabajado(self):
        """Verifica si el día fue trabajado (asignado y sin falta registrada)."""
        falta = Asistencia.objects.filter(empleado=self.empleado, fecha=self.fecha).exists()
        return not falta  # Si hay falta, no cuenta como trabajado

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ('empleado', 'fecha')  # Evita registros duplicados por día y empleado

   
class Nomina(models.Model):
    fecha_inicio = models.DateField("Fecha de Inicio")  # Fecha seleccionada por el usuario
    fecha_fin = models.DateField("Fecha de Fin")  # Se puede calcular automáticamente
    total_percepciones = models.DecimalField("Total Percepciones", max_digits=12, decimal_places=2, default=0.00)
    total_deducciones = models.DecimalField("Total Deducciones", max_digits=12, decimal_places=2, default=0.00)
    total_neto = models.DecimalField("Total Neto", max_digits=12, decimal_places=2, default=0.00)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.PROTECT, related_name="nominas")  # Cuenta a afectar
    estado = models.CharField(
        "Estado", max_length=10, choices=[("Abierta", "Abierta"), ("Cerrada", "Cerrada")], default="Abierta"
    )  # Control de cierre

    def cerrar_nomina(self):
        """Descuenta de la cuenta y cierra la nómina."""
        if self.estado == "Abierta" and self.cuenta.saldo_actual >= self.total_neto:
            self.cuenta.saldo_actual -= self.total_neto
            self.cuenta.save()
            self.estado = "Cerrada"
            self.save()
            return True
        return False  # No se puede cerrar (saldo insuficiente)

    def __str__(self):
        return f"Nómina {self.fecha_inicio} - {self.fecha_fin} ({self.estado})"

class Prestaciones(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    vacaciones_acumuladas = models.IntegerField(default=0)
    aguinaldo_acumulado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def calcular_prestaciones(self):
        self.vacaciones_acumuladas = self.empleado.antiguedad() * 6  # Suponiendo 6 días por año
        self.aguinaldo_acumulado = (self.empleado.sueldo_diario * 15) / 365 * (date.today() - self.empleado.ingreso).days
        self.save()
    
    def __str__(self):
        return f"Prestaciones {self.empleado.nombre}"


# class NominaHistorial(models.Model):
#      periodo_inicio = models.DateField(unique=True)  # Fecha de inicio del período
#      periodo_fin = models.DateField()  # Fecha de fin del período
#      total_pago = models.DecimalField(max_digits=12, decimal_places=2)
#      cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
#      ESTATUS_CHOICES = [
#          ('Pendiente', 'Pendiente'),
#          ('Procesada', 'Procesada'),
#          ('Cancelada', 'Cancelada'),
#      ]
    
#      estatus = models.CharField(max_length=10, choices=ESTATUS_CHOICES, default='Pendiente')
#      fecha_procesada = models.DateTimeField(null=True, blank=True)

#      class Meta:
#          unique_together = ('periodo_inicio', 'periodo_fin')  # Evita duplicados del mismo período

#      def save(self, *args, **kwargs):
#          if self.estatus == 'Procesada':
#              # Validar que no exista otra nómina en el mismo período
#              if NominaHistorial.objects.filter(periodo_inicio=self.periodo_inicio, estatus='Procesada').exists():
#                  raise ValueError("Ya existe una nómina procesada en este período")
#              self.fecha_procesada = timezone.now()
        
#          super().save(*args, **kwargs)

#      def __str__(self):
#          return f"Nómina {self.periodo_inicio} - {self.periodo_fin} - {self.estatus} - Total: {self.total_pago}"



class NominaHistorial(models.Model):
    periodo_inicio = models.DateField(unique=True)
    periodo_fin = models.DateField()
    total_pago = models.DecimalField(max_digits=12, decimal_places=2)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE,null=True,blank=True)

    ESTATUS_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Procesada', 'Procesada'),
        ('CERRADO', 'Cerrado'),
        ('Cancelada', 'Cancelada'),
    ]

    estatus = models.CharField(max_length=10, choices=ESTATUS_CHOICES, default='Pendiente')
    fecha_procesada = models.DateTimeField(null=True, blank=True)
    periodo_nomina = models.ForeignKey('PeriodosNomina', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('periodo_inicio', 'periodo_fin')

    def save(self, *args, **kwargs):
        # Asignar automáticamente el período de nómina si no está definido
        if not self.periodo_nomina:
            self.periodo_nomina = self.get_periodo_nomina()

        if self.estatus == 'Procesada':
            # Validar que no exista otra nómina procesada en el mismo período
            qs = NominaHistorial.objects.filter(
                periodo_inicio=self.periodo_inicio,
                estatus='Procesada'
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValueError("Ya existe una nómina procesada en este período.")

            # Asignar fecha si no la tenía antes
            if not self.fecha_procesada:
                self.fecha_procesada = timezone.now()
        else:
            self.fecha_procesada = None

        super().save(*args, **kwargs)

    def get_periodo_nomina(self):
        return PeriodosNomina.objects.filter(
            periodo_inicio=self.periodo_inicio,
            periodo_final=self.periodo_fin
        ).first()

    def __str__(self):
        return self.semana_texto

    @property
    def semana_texto(self):
        if self.periodo_nomina:
            return f"Semana {self.periodo_nomina.semana} ({self.periodo_inicio} al {self.periodo_fin}) - {self.estatus}"
        return f"Periodo {self.periodo_inicio} al {self.periodo_fin} - {self.estatus}"



class NominaDetalle(models.Model):
    nomina_empleado = models.ForeignKey('NominaEmpleado', on_delete=models.CASCADE, related_name="detalles")
    concepto = models.CharField(max_length=120, null=True,blank=True)
    tipo = models.CharField(max_length=15, choices=[('PERCEPCION', 'Percepción'), ('DEDUCCION', 'Deducción')])
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    monto_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Detalle de Nómina"
        verbose_name_plural = "Detalles de Nómina"

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.monto_unitario
        super().save(*args, **kwargs)


class PeriodosNomina(models.Model):
    anio = models.PositiveIntegerField(null=True,blank=True)
    semana = models.IntegerField(null=False,blank=False,default=0)
    periodo_inicio = models.DateField()
    periodo_final  = models.DateField()
    fecha_corte = models.DateField()
    dia_pago = models.DateField()
    ESTATUS_CHOICES = [
        ('ABIERTO', 'Abierto'),
        ('EN PROCESO', 'En Proceso'),
        ('CERRADO', 'Cerrado'),
        ('CANCELADO', 'Cancelado'),
    ]
    estatus = models.CharField(max_length=15, choices=ESTATUS_CHOICES, default='ABIERTO')


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['anio', 'semana'], name='unique_anio_semana')
        ]
        ordering = ['-anio', '-semana']

    def __str__(self):
        return f"Semana {self.semana} | {self.periodo_inicio} al {self.periodo_final} | {self.estatus}"


    

class AsignacionDiaria(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha = models.DateField()
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.SET_NULL, null=True, blank=True)
    horas_trabajadas = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        unique_together = (('empleado', 'fecha', 'proyecto'),)

    def clean(self):
        # Validar unicidad en el nivel de aplicación
        if AsignacionDiaria.objects.filter(
            empleado=self.empleado,
            fecha=self.fecha,
            proyecto=self.proyecto
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"Ya existe una asignación para {self.empleado} en {self.fecha} con el proyecto {self.proyecto or 'Sin Proyecto'}."
            )
        # Validar horas totales por día (opcional, máximo 12 horas)
        total_horas = AsignacionDiaria.objects.filter(
            empleado=self.empleado,
            fecha=self.fecha
        ).exclude(pk=self.pk).aggregate(total=Sum('horas_trabajadas'))['total'] or 0
        if total_horas + self.horas_trabajadas > 12:
            raise ValidationError("El total de horas por día no puede exceder 12.")
    

class MovimientoCuentaProyecto(models.Model):
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.CASCADE, related_name='movimientos')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    periodo = models.ForeignKey(NominaHistorial, on_delete=models.CASCADE)  # Nómina cerrada
    importe = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.empleado.nombre} - {self.importe}"
    

# Modelo para registro de asistencia (reloj checador)
class RegistraAsistencia(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_hora_entrada = models.DateTimeField()
    fecha_hora_salida = models.DateTimeField(blank=True, null=True)
    latitud = models.FloatField()
    longitud = models.FloatField()
    origen = models.CharField(max_length=20, default="whatsapp",null=True,blank=True)

    def __str__(self):
        return f"Asistencia de {self.usuario} - {self.fecha_hora_entrada}"
    



class TarifaDiariaObra(models.Model):
    """
    $/día por obra y (opcional) empleado o rol.
    Si ya tienes tueldos fijos por empleado, puedes convertir esto en override por obra.
    """
    obra = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, null=True, blank=True, on_delete=models.CASCADE)
    monto_dia = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("obra", "empleado")

    def __str__(self):
        who = self.empleado.nombre if self.empleado else "General"
        return f"{self.obra} - {who}: ${self.monto_dia}/día"


class AsistenciaDia(models.Model):
    """
    Marca 1/0 o fracción por día y horas extra.
    """
    semana = models.ForeignKey(PeriodosNomina, on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    obra = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    fecha = models.DateField()
    laboro = models.DecimalField(max_digits=4, decimal_places=2, default=1)  # permite 0.5, etc.
    horas_extra = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ("empleado", "fecha")


class TipoDestajo(models.Model):
    """
    Catálogo de destajos: p.ej. 'm3 excavación', 'caja ciega', 'registro 50%', 'viaje tepetate', etc.
    """
    nombre = models.CharField(max_length=120, unique=True)
    unidad = models.CharField(max_length=30, default="pieza")  # m3, pza, viaje, etc.

    def __str__(self):
        return self.nombre


class TarifaDestajoObra(models.Model):
    """
    Tarifa variable por obra y por tipo de destajo.
    """
    obra = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoDestajo, on_delete=models.CASCADE)
    tarifa = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        unique_together = ("obra", "tipo")


class RegistroDestajo(models.Model):
    """
    Movimiento de destajo: quién lo hizo, dónde, cuánto, y precio aplicable.
    Permite factor (p.ej. 0.5 cuando dice 50%) y override puntual de tarifa.
    """
    semana = models.ForeignKey(PeriodosNomina, on_delete=models.CASCADE)
    obra = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    empleado = models.ForeignKey(Empleado, null=True, blank=True, on_delete=models.SET_NULL)
    tipo = models.ForeignKey(TipoDestajo, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    factor = models.DecimalField(max_digits=8, decimal_places=4, default=1)  # ej. 0.5
    tarifa_aplicada = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    descripcion = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        self.total = self.calcular_total()
        super().save(*args, **kwargs)


    def calcular_total(self):
        base = self.tarifa_aplicada
        if base is None:
            # Buscar tarifa por obra+tipo
            try:
                base = TarifaDestajoObra.objects.get(obra=self.obra, tipo=self.tipo).tarifa
            except TarifaDestajoObra.DoesNotExist:
                base = 0
        return round(base * self.cantidad * self.factor, 2)


class GastoObra(models.Model):
    """
    Otros gastos imputados a obra durante la semana (viáticos, arena, piedra, llantera, etc.)
    """
    semana = models.ForeignKey(PeriodosNomina, on_delete=models.CASCADE)
    obra = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    concepto = models.CharField(max_length=160)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    proveedor = models.CharField(max_length=160, blank=True, default="")
    observaciones = models.TextField(blank=True, default="")

class HorasExtras(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    periodo = models.ForeignKey(PeriodosNomina, on_delete=models.CASCADE)
    proyecto = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE, null=True, blank=True)
    fecha = models.DateField()
    horas = models.DecimalField(max_digits=6, decimal_places=2)
    pago_por_hora = models.DecimalField(max_digits=10, decimal_places=2)
    total_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        # ✅ Calcula automáticamente el pago por hora según el sueldo diario del empleado
        if self.empleado and self.empleado.sueldo_diario:
            sueldo_diario = Decimal(self.empleado.sueldo_diario or 0)
            self.pago_por_hora = (sueldo_diario / Decimal(8)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.pago_por_hora = Decimal("0.00")

        # ✅ Calcula total pago automáticamente
        self.total_pago = (self.horas * self.pago_por_hora).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.empleado.nombre} - {self.horas} hrs (${self.total_pago})"

    class Meta:
        verbose_name = "Hora extra"
        verbose_name_plural = "Horas extras"
        ordering = ["-fecha"]
        
        


class NominaEmpleado(models.Model):
    historial = models.ForeignKey(NominaHistorial, on_delete=models.CASCADE, related_name='empleados')
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.SET_NULL, null=True, blank=True)
    total_percepciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deducciones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dias_trabajados = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    horas_trabajadas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('historial', 'empleado', 'proyecto')
        verbose_name = "Nómina por empleado"
        verbose_name_plural = "Nóminas por empleado"

    def __str__(self):
        return f"{self.empleado.nombre} ({self.proyecto or 'Sin proyecto'}) - {self.total_neto}"



class NominaAcumulado(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    proyecto = models.ForeignKey('adm.Proyecto', on_delete=models.SET_NULL, null=True, blank=True)
    periodo = models.ForeignKey(PeriodosNomina, on_delete=models.SET_NULL, null=True, blank=True)
    mes = models.IntegerField()
    anio = models.PositiveIntegerField()
    dias_trabajados = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sueldo_diario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    horas_extras = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    compensacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    destajo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importe = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('empleado', 'mes', 'anio', 'proyecto', 'periodo')
        verbose_name = "Acumulado mensual"
        verbose_name_plural = "Acumulados mensuales"

    def __str__(self):
        return f"{self.empleado.nombre} - {self.anio}/{self.mes}"



class CompensacionVariable(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    periodo = models.ForeignKey(PeriodosNomina, on_delete=models.CASCADE)
    proyecto = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE, null=True, blank=True)
    fecha = models.DateField()
    concepto = models.CharField(max_length=100, default="Compensación variable")
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.empleado.nombre} - {self.concepto} (${self.monto})"

    class Meta:
        verbose_name = "Compensación variable"
        verbose_name_plural = "Compensaciones variables"
        ordering = ["-fecha"]


class ActividadObra(models.Model):
    nombre = models.CharField(max_length=150)
    unidad = models.CharField(max_length=20)  # m2, m3, ml, pieza
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.unidad})"




class RendimientoActividad(models.Model):
    actividad = models.ForeignKey(ActividadObra, on_delete=models.CASCADE)
    perfil = models.ForeignKey(PerfilPuesto, on_delete=models.CASCADE)

    rendimiento = models.DecimalField(max_digits=10, decimal_places=2)
    # Ejemplo: 12 m2 por día

    def __str__(self):
        return f"{self.perfil} - {self.actividad} ({self.rendimiento}/día)"


class CostoActividad(models.Model):
    actividad = models.ForeignKey(ActividadObra, on_delete=models.CASCADE)
    perfil = models.ForeignKey(PerfilPuesto, on_delete=models.CASCADE)

    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def calcular_costo(self):
        rendimiento = RendimientoActividad.objects.get(
            actividad=self.actividad,
            perfil=self.perfil
        ).rendimiento

        sueldo = (self.perfil.sueldo_min + self.perfil.sueldo_max) / 2

        # costo por unidad (ej: por m2)

        self.costo_unitario = sueldo / rendimiento


class EjecucionActividad(models.Model):
    fecha = models.DateField()
    proyecto = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)

    actividad = models.ForeignKey(ActividadObra, on_delete=models.CASCADE)
    perfil = models.ForeignKey(PerfilPuesto, on_delete=models.CASCADE)

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)

    costo_real = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        costo = CostoActividad.objects.get(
            actividad=self.actividad,
            perfil=self.perfil
        ).costo_unitario

        self.costo_real = self.cantidad * costo
        super().save(*args, **kwargs)


class PresupuestoActividad(models.Model):
    proyecto = models.ForeignKey("adm.Proyecto", on_delete=models.CASCADE)
    actividad = models.ForeignKey(ActividadObra, on_delete=models.CASCADE)

    cantidad_estimado = models.DecimalField(max_digits=10, decimal_places=2)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2)


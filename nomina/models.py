from django.db import models
from django.contrib.auth.models import User
from bases.models import ClaseModelo
from adm.models import Cuenta
from inv.models import Material
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
import re
from django.utils import timezone
from datetime import date, timedelta


# Create your models here.
class Empleado(ClaseModelo):
    codigo = models.IntegerField('Codigo',default=0,blank=False,null=False,unique=True)
    curp = models.CharField('Curp',max_length=18,blank=False,null=False,unique=True)
    rfc  = models.CharField('Rfc',max_length=13,null=False,blank=False,default='')
    nombre = models.CharField('Nombre',max_length=120,blank=False,null=False,default='')
    ingreso = models.DateField('Ingreso',blank=False,null=False)
    sueldo_diario = models.DecimalField('Sueldo diario',max_digits=10,decimal_places=2,default=0.00)
    compensacion = models.DecimalField('Compensación',decimal_places=2,max_digits=10,default=0.00,blank=True,null=True)
    puesto = models.CharField('Puesto',max_length=80,blank=True,null=True,default='AUXILIAR GENERAL')

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

    def save(self):
        self.curp    = self.curp.upper()
        self.nombre  = self.nombre.upper()
        self.puesto  = self.puesto.upper()
        self.rfc     = self.rfc.upper()
        super(Empleado, self).save()
        
    def __str__(self):
        return self.nombre+" "+self.puesto
    
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


class NominaHistorial(models.Model):
     periodo_inicio = models.DateField(unique=True)  # Fecha de inicio del período
     periodo_fin = models.DateField()  # Fecha de fin del período
     total_pago = models.DecimalField(max_digits=12, decimal_places=2)
     cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
     ESTATUS_CHOICES = [
         ('Pendiente', 'Pendiente'),
         ('Procesada', 'Procesada'),
         ('Cancelada', 'Cancelada'),
     ]
    
     estatus = models.CharField(max_length=10, choices=ESTATUS_CHOICES, default='Pendiente')
     fecha_procesada = models.DateTimeField(null=True, blank=True)

     class Meta:
         unique_together = ('periodo_inicio', 'periodo_fin')  # Evita duplicados del mismo período

     def save(self, *args, **kwargs):
         if self.estatus == 'Procesada':
             # Validar que no exista otra nómina en el mismo período
             if NominaHistorial.objects.filter(periodo_inicio=self.periodo_inicio, estatus='Procesada').exists():
                 raise ValueError("Ya existe una nómina procesada en este período")
             self.fecha_procesada = timezone.now()
        
         super().save(*args, **kwargs)

     def __str__(self):
         return f"Nómina {self.periodo_inicio} - {self.periodo_fin} - {self.estatus} - Total: {self.total_pago}"

    
    

class NominaDetalle(models.Model):
     nomina_historica = models.ForeignKey(NominaHistorial, on_delete=models.CASCADE, related_name="detalles")
     empleado = models.ForeignKey('Empleado', on_delete=models.CASCADE)  # Asumiendo que tienes un modelo Empleado
     sueldo_diario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
     dias_trabajados = models.IntegerField(default=0)
     total_pago = models.DecimalField(max_digits=10, decimal_places=2,default=0.00)

     
     def __str__(self):
         return f"{self.empleado} - {self.total_pago}"


class PeriodosNomina(models.Model):
    semana = models.IntegerField(null=False,blank=False,default=0)
    periodo_inicio = models.DateField()
    periodo_final  = models.DateField()
    fecha_corte = models.DateField()
    dia_pago = models.DateField()

    def __str__(self):
        return f"{self.semana} - {self.periodo_inicio} - {self.periodo_final}"
    




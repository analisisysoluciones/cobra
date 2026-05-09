from django.db import models
from adm.models import Equipo
from django.db.models import Max
from django.utils import timezone
# Create your models here.
class TarifaEquipo(models.Model):

    TIPO_COBRO = [
        ("HORA", "Por hora"),
        ("DIA", "Por día"),
        ("JORNADA", "Por jornada"),
        ("EVENTO", "Por evento"),
    ]

    equipo = models.ForeignKey("adm.Equipo", on_delete=models.PROTECT)

    tipo_cobro = models.CharField(max_length=10, choices=TIPO_COBRO)

    precio = models.DecimalField(max_digits=10, decimal_places=2)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.equipo} - {self.tipo_cobro} - {self.precio}"

    
class Cliente(models.Model):
    codigo = models.CharField(max_length=20, unique=True,  blank=True)

    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    direccion = models.TextField(blank=True)

    rfc = models.CharField(max_length=13, blank=True)

    activo = models.BooleanField(default=True)

    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre        
    
    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        if not self.codigo:
            ultimo_codigo = Cliente.objects.aggregate(
                max_codigo=Max("codigo")
            )["max_codigo"]

            if ultimo_codigo:
                numero = int(ultimo_codigo.replace("CR", ""))
                siguiente = numero + 1
            else:
                siguiente = 1

            self.codigo = f"CR{str(siguiente).zfill(5)}"

        super().save(*args, **kwargs)


    

class RentaEquipo(models.Model):

    ESTATUS = [
        ("ACTIVA", "Activa"),
        ("FINALIZADA", "Finalizada"),
        ("CANCELADA", "Cancelada"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)

    equipo = models.ForeignKey("adm.Equipo", on_delete=models.PROTECT)

    tarifa = models.ForeignKey(TarifaEquipo, on_delete=models.PROTECT)

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)

    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Horas, días, jornadas, etc."
    )

    importe = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    observaciones = models.TextField(blank=True)

    estatus = models.CharField(max_length=12, choices=ESTATUS, default="ACTIVA")

    creado = models.DateTimeField(auto_now_add=True)


    def calcular_importe(self):

        if not (self.fecha_inicio and self.fecha_fin and self.tarifa):
            return

        delta = self.fecha_fin - self.fecha_inicio
        horas = delta.total_seconds() / 3600

        tipo = self.tarifa.tipo_cobro
        precio = float(self.tarifa.precio)

        if tipo == "HORA":

            self.cantidad = round(horas, 2)
            self.importe = round(self.cantidad * precio, 2)

        elif tipo == "JORNADA":

            horas_base = 8

            if horas <= horas_base:
                self.cantidad = 1
                self.importe = precio
            else:
                extra = horas - horas_base
                self.cantidad = round(horas, 2)
                self.importe = round(precio + (extra * (precio / horas_base)), 2)

        elif tipo == "DIA":

            self.cantidad = 1
            self.importe = precio

        elif tipo == "EVENTO":

            self.cantidad = 1
            self.importe = precio
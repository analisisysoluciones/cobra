from django.db import models
from adm.models import Equipo
from django.db.models import Max
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
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
    folio = models.CharField(max_length=30,blank=True,null=True)

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
    subtotal_conceptos = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    total = models.DecimalField(max_digits=12,decimal_places=2,default=0)

    observaciones = models.TextField(blank=True)

    estatus = models.CharField(max_length=12, choices=ESTATUS, default="ACTIVA")
    ESTATUS_FINANCIERO = [

    ("PENDIENTE", "Pendiente"),

    ("ABONO", "Abono"),

    ("PAGADA", "Pagada"),

    ]

    estatus_financiero = models.CharField(max_length=15,choices=ESTATUS_FINANCIERO,default="PENDIENTE")

    creado = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):

        creando = self.pk is None

        super().save(*args, **kwargs)

        if creando and not self.folio:

            anio = self.creado.year

            self.folio = (
                f"REN-{anio}-{str(self.pk).zfill(6)}"
            )

            super().save(
                update_fields=["folio"]
            )


    def calcular_importe(self):

        if not (
            self.fecha_inicio and
            self.fecha_fin and
            self.tarifa
        ):
            return

        delta = self.fecha_fin - self.fecha_inicio

        horas = Decimal(
            str(
                delta.total_seconds() / 3600
            )
        )

        tipo = self.tarifa.tipo_cobro

        precio = Decimal(
            str(self.tarifa.precio)
        )

        if tipo == "HORA":

            self.cantidad = horas.quantize(
                Decimal("0.01")
            )

            self.importe = (
                self.cantidad * precio
            )

        elif tipo == "JORNADA":

            horas_base = Decimal("8")

            if horas <= horas_base:

                self.cantidad = Decimal("1")

                self.importe = precio

            else:

                extra = horas - horas_base

                self.cantidad = horas.quantize(
                    Decimal("0.01")
                )

                valor_hora = (
                    precio / horas_base
                )

                self.importe = (
                    precio +
                    (extra * valor_hora)
                )

        elif tipo == "DIA":

            self.cantidad = Decimal("1")

            self.importe = precio

        elif tipo == "EVENTO":

            self.cantidad = Decimal("1")

            self.importe = precio


        self.importe = self.importe.quantize(
            Decimal("0.01")
        )



    def actualizar_totales(self):

        subtotal = (
            self.conceptos.aggregate(
                total=Sum("importe")
            )["total"]
            or Decimal("0.00")
        )

        self.subtotal_conceptos = subtotal

        self.total = (
            self.importe +
            subtotal
        )
        

    def actualizar_estado_financiero(self):

        total_pagado = sum(

            (
                p.importe
                for p in self.pagos.all()
            ),

            Decimal("0.00")

        )

        saldo = (
            Decimal(str(self.total)) -
            total_pagado
        ).quantize(
            Decimal("0.01")
        )

        if saldo == Decimal("0.00"):

            self.estatus_financiero = (
                "PAGADA"
            )

        elif total_pagado > Decimal("0.00"):

            self.estatus_financiero = (
                "ABONO"
            )

        else:

            self.estatus_financiero = (
                "PENDIENTE"
            )

        self.save(
            update_fields=[
                "estatus_financiero"
            ]
        )

    @property
    def total_conceptos(self):

        return sum(
            c.importe
            for c in self.conceptos.all()
        )


    @property
    def total_final(self):

        return (
            self.importe +
            self.total_conceptos
        )


class ConceptoRentaCatalogo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    precio_default = models.DecimalField(max_digits=12,decimal_places=2,default=0)

    class Meta:
        verbose_name = "Concepto de renta"
        verbose_name_plural = "Conceptos de renta"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RentaConcepto(models.Model):

    renta = models.ForeignKey(
        "RentaEquipo",
        on_delete=models.CASCADE,
        related_name="conceptos"
    )

    concepto = models.ForeignKey(
        ConceptoRentaCatalogo,
        on_delete=models.PROTECT
    )

    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    importe = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    observaciones = models.CharField(
        max_length=250,
        blank=True
    )

    creado = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Concepto renta"
        verbose_name_plural = "Conceptos renta"

    def save(self, *args, **kwargs):

        self.importe = (
            self.cantidad * self.precio
        )

        super().save(*args, **kwargs)

    def __str__(self):

        return (
            f"{self.renta_id} - "
            f"{self.concepto}"
        )                    
        
        
class PagoRenta(models.Model):

    METODOS = [

        ("EFECTIVO", "Efectivo"),

        ("TRANSFERENCIA", "Transferencia"),

        ("TARJETA", "Tarjeta"),

        ("CHEQUE", "Cheque"),

    ]

    renta = models.ForeignKey(

        RentaEquipo,

        on_delete=models.PROTECT,

        related_name="pagos"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS,
        default="EFECTIVO"
    )

    referencia = models.CharField(
        max_length=100,
        blank=True
    )

    importe = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    observaciones = models.TextField(
        blank=True
    )

    creado_por = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,

        null=True,
        blank=True
    )

    def __str__(self):

        return (
            f"{self.renta.folio} - "
            f"${self.importe}"
        )        
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from adm.models import Cuenta, Proyecto  # AJUSTAR si tus modelos están en otra app
from django.contrib import messages
from django.shortcuts import redirect

ESTATUS = [
    ("PENDIENTE", "Pendiente"),
    ("AFECTADO", "Afectado"),
]



class IngresoExtraordinario(models.Model):

    TIPO_INGRESO = [
        ("PRESTAMO", "Préstamo recibido"),
        ("DEVOLUCION_PRESTAMO", "Devolución de préstamo"),
        ("APORTACION_SOCIOS", "Aportación de capital de socios"),
        ("ANTICIPO_OBRA", "Anticipo de obra"),
        ("VENTAS", "Ventas"),
        ("COMISIONES", "Comisiones"),

        # Recomendados por contabilidad
        ("REEMBOLSO_PROVEEDOR", "Reembolso proveedor"),
        ("REEMBOLSO_GASTOS", "Reembolso de gastos"),
        ("TRASPASO_INTERNO", "Traspaso entre cuentas bancarias"),
        ("AJUSTE_BANCARIO", "Ajuste bancario positivo"),
        ("INTERESES", "Intereses ganados"),
        ("DIF_CAMBIO", "Diferencia cambiaria a favor"),
        ("VENTA_ACTIVO", "Venta de activo / herramienta"),
        ("RECUP_CAJA_CHICA", "Recuperación de caja chica"),
        ("DONACION", "Donación recibida"),
        ("INGRESO_EXTRA", "Ingreso extraordinario"),
        ("PENDIENTE_IDENTIFICAR", "Ingreso no identificado (en aclaración)"),
    ]
    folio = models.PositiveIntegerField(unique=True, null=True, blank=True)
    fecha = models.DateField(default=timezone.now)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)

    proyecto = models.ForeignKey(
        'adm.Proyecto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Solo aplica para anticipos de obra o ingresos ligados a proyectos."
    )

    tipo = models.CharField(max_length=40, choices=TIPO_INGRESO)
    concepto = models.CharField(max_length=200)
    referencia = models.CharField(max_length=150, null=True, blank=True)

    monto = models.DecimalField(max_digits=12, decimal_places=2)

    creado = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    estatus = models.CharField(max_length=15, choices=ESTATUS, default="PENDIENTE")
    fecha_afectado = models.DateTimeField(null=True, blank=True)


    def save(self, *args, **kwargs):
        # SOLO cuando se crea por primera vez aumentar saldo
        if not self.pk:
            self.cuenta.saldo_actual += self.monto
            self.cuenta.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.monto:,.2f} ({self.fecha})"

    def form_valid(self, form):
        ingreso = form.save(commit=False)
        ingreso.usuario = self.request.user
        ingreso.save()

        # Actualizar saldo de la cuenta
        cuenta = ingreso.cuenta
        cuenta.saldo_actual += ingreso.monto
        cuenta.save()

        messages.success(self.request, "Ingreso registrado correctamente y cuenta actualizada.")
        return super().form_valid(form)
    
    def delete(self, request, *args, **kwargs):
        ingreso = self.get_object()
        cuenta = ingreso.cuenta

        # Revertir saldo
        cuenta.saldo_actual -= ingreso.monto
        cuenta.save()

        messages.success(request, "Ingreso eliminado y saldo revertido.")
        return super().delete(request, *args, **kwargs)
    
    def dispatch(self, request, *args, **kwargs):
        ingreso = self.get_object()
        if ingreso.estatus == "AFECTADO":
            messages.error(request, "No puedes eliminar un ingreso ya afectado.")
            return redirect("finanzas:ingreso_detail", pk=ingreso.id)
        return super().dispatch(request, *args, **kwargs)



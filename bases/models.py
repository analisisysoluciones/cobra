from django.db import models, transaction
from django.contrib.auth.models import User
from django.views import generic
from django.utils import timezone

class ClaseModelo(models.Model):
      estado = models.BooleanField(default=True)
      fc = models.DateTimeField(auto_now_add=True)
      fm = models.DateTimeField(auto_now=True)
      uc = models.ForeignKey(User, on_delete=models.CASCADE)
      um = models.IntegerField(blank=True,null=True)

      class Meta:
            abstract = True


class Folios(models.Model):
    tipo_documento = models.CharField('Documento:',max_length=12,unique=True,blank=False,null=False)
    anio = models.PositiveIntegerField(default=timezone.now().year)
    consecutivo = models.PositiveIntegerField(default=1)


    class Meta:
        verbose_name = "Folio"
        verbose_name_plural = "Folios"

    def __str__(self):
        return f"{self.tipo_documento.tipo} - {self.anio} - {self.consecutivo:04d}"

    def next_consecutivo(self):
        """Incrementa y retorna el próximo consecutivo."""
        with transaction.atomic():
            self.consecutivo += 1
            self.save()
            return f"{self.anio}-{self.consecutivo:04d}"
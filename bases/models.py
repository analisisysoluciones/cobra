from django.db import models, transaction
from django.contrib.auth.models import User
from django.views import generic
from django.utils import timezone

import logging

logger = logging.getLogger(__name__)

class ClaseModelo(models.Model):
      estado = models.BooleanField(default=True)
      fc = models.DateTimeField(auto_now_add=True)
      fm = models.DateTimeField(auto_now=True)
      uc = models.ForeignKey(User, on_delete=models.CASCADE,related_name="%(class)s_creado_por")
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
        return f"{self.tipo_documento} - {self.anio} - {self.consecutivo:04d}"
    
    def next_consecutivo(self):
        """Incrementa y retorna el próximo consecutivo, asegurando unicidad."""
        from cxp.models import CompraEnc
        with transaction.atomic():
            # Bloquea el registro para evitar condiciones de carrera
            folio_registro = Folios.objects.select_for_update().get(pk=self.pk)
            folio_registro.consecutivo += 1
            folio_registro.save()
            nuevo_folio = f"{folio_registro.anio}-{folio_registro.consecutivo:04d}"
            logger.debug(f"Generando folio: {nuevo_folio}")
            # Verifica si el folio ya existe en CompraEnc
            while CompraEnc.objects.filter(folio_documento=nuevo_folio).exists():
                folio_registro.consecutivo += 1
                folio_registro.save()
                nuevo_folio = f"{folio_registro.anio}-{folio_registro.consecutivo:04d}"
                logger.debug(f"Folio {nuevo_folio} ya existe, generando nuevo: {nuevo_folio}")
            return nuevo_folio
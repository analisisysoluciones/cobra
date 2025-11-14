import csv
from django.core.management.base import BaseCommand
from cxp.models import CompraEnc
from django.utils import timezone

class Command(BaseCommand):
    help = "Genera un reporte de compras en formato CSV"

    def handle(self, *args, **options):
        fecha_hoy = timezone.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"reporte_compras_{fecha_hoy}.csv"

        with open(nombre_archivo, mode="w", newline='', encoding="utf-8") as archivo:
            writer = csv.writer(archivo)
            writer.writerow([
                "ID",
                "Fecha",
                "Tipo Documento",
                "Proveedor",
                "Proyecto",
                "Total",
                "Estado",
                "Usuario Captura"
            ])

            compras = CompraEnc.objects.select_related('tipo', 'proveedor', 'proyecto', 'uc').order_by('-fecha')
            
            for c in compras:
                writer.writerow([
                    c.id,
                    c.fecha.strftime("%d/%m/%Y") if c.fecha else "",
                    c.tipo.descripcion if hasattr(c.tipo, 'descripcion') else str(c.tipo),
                    c.proveedor.nombre if hasattr(c.proveedor, 'nombre') else str(c.proveedor),
                    c.proyecto.nombre if hasattr(c.proyecto, 'nombre') else str(c.proyecto),
                    float(c.total),
                    c.estado or "",
                    c.uc.username if c.uc else "",
                ])

        self.stdout.write(self.style.SUCCESS(f"✅ Archivo generado: {nombre_archivo}"))

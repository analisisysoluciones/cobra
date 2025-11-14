import csv
import os
from decimal import Decimal
from django.utils import timezone
import django

# === CONFIGURACIÓN BASE DJANGO ===
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cobra.settings')
django.setup()

from ventas.models import ProductoInmobiliario
from django.contrib.auth.models import User

# === CONFIGURA TUS PARÁMETROS ===
PROYECTO_ID = 3  # Proyecto Los Sauces
USUARIO = User.objects.filter(username="creador").first() or User.objects.first()
CSV_PATH = "/home/creador/cobra/sauces.csv"  # Ruta absoluta al CSV en el VPS

def limpiar_decimal(valor):
    """Convierte precios tipo '$505,920.00' a Decimal('505920.00')."""
    if not valor:
        return Decimal("0.00")
    try:
        return Decimal(
            str(valor)
            .replace("$", "")
            .replace(",", "")
            .replace(" ", "")
            .strip()
        )
    except Exception:
        return Decimal("0.00")

def importar_productos():
    nuevos = 0
    actualizados = 0
    omitidos = 0

    with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            clave = row.get("CLAVE", "").strip()
            manzana = row.get("MANZANA", "").strip()
            lote = row.get("LOTE", "").strip()
            medidas = row.get("M2", "").strip()
            precio = limpiar_decimal(row.get("PRECIO", "0"))
            status = row.get("STATUS", "").strip()

            if not clave:
                print(f"⚠️  Fila sin clave, omitida: {row}")
                omitidos += 1
                continue

            # Determinar proceso
            proceso = "Vendido" if status.lower() == "vendido" else "Disponible"

            obj, created = ProductoInmobiliario.objects.update_or_create(
                clave=int(clave),
                proyecto_id=PROYECTO_ID,
                defaults={
                    "manzana": manzana,
                    "lote": lote,
                    "medidas": medidas,
                    "precio": precio,
                    "saldo": precio,
                    "proceso": proceso,
                    "tipo": 1,
                    "uc": USUARIO,
                    "um": USUARIO,
                    "fc": timezone.now(),
                    "fm": timezone.now(),
                },
            )

            if created:
                nuevos += 1
            else:
                actualizados += 1

    print("✅ Importación completada.")
    print(f"   Nuevos registros: {nuevos}")
    print(f"   Actualizados: {actualizados}")
    print(f"   Omitidos: {omitidos}")

if __name__ == "__main__":
    importar_productos()

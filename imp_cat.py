import os
import django
import csv
from slugify import slugify  # pip install python-slugify

# ----------------------------------
# CONFIGURAR DJANGO
# ----------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cobra.settings')
django.setup()

# ----------------------------------
# IMPORTS
# ----------------------------------
from nomina.models import PerfilPuesto


# ----------------------------------
# CONFIG
# ----------------------------------
CSV_PATH = 'catalogo.csv'


# ----------------------------------
# FUNCION PRINCIPAL
# ----------------------------------
def importar():

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:

            nombre = row["nombre"].strip()
            categoria = row["categoria"].strip().upper()
            sueldo_min = float(row["sueldo_min"])
            sueldo_max = float(row["sueldo_max"])

            # 🔑 LLAVE ÚNICA
            slug = slugify(nombre)

            obj, created = PerfilPuesto.objects.update_or_create(
                slug=slug,
                defaults={
                    "nombre": nombre,
                    "categoria": categoria,
                    "sueldo_min": sueldo_min,
                    "sueldo_max": sueldo_max,
                    "activo": True
                }
            )

            if created:
                print(f"✔ Creado: {nombre}")
            else:
                print(f"↻ Actualizado: {nombre}")


# ----------------------------------
# EJECUCION
# ----------------------------------
if __name__ == "__main__":
    print("🚀 Importando catálogo de perfiles...")
    importar()
    print("✅ Proceso terminado")
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cobra.settings")
django.setup()

from adm.models import ActividadEquipo, TipoEquipo

# ============================
# DATA BASE
# ============================

DATA = [
    ("Excavación", "PRODUCTIVO", ["Retroexcavadora"]),
    ("Carga de material", "PRODUCTIVO", ["Retroexcavadora", "Volteo"]),
    ("Descarga de material", "PRODUCTIVO", ["Volteo"]),
    ("Nivelación", "PRODUCTIVO", ["Niveladora"]),
    ("Compactación", "PRODUCTIVO", ["Compactador"]),

    ("Traslado", "SOPORTE", ["Retroexcavadora", "Volteo", "Niveladora"]),
    ("Maniobra", "SOPORTE", ["Retroexcavadora", "Volteo"]),
    ("Abastecimiento de combustible", "SOPORTE", ["Retroexcavadora", "Volteo"]),
    ("Revisión", "SOPORTE", ["Retroexcavadora", "Volteo"]),

    ("Espera por material", "MUERTO", ["Retroexcavadora", "Volteo"]),
    ("Espera por operador", "MUERTO", ["Retroexcavadora", "Volteo"]),
    ("Paro por falla", "MUERTO", ["Retroexcavadora", "Volteo", "Niveladora"]),
    ("Paro por clima", "MUERTO", ["Retroexcavadora", "Volteo", "Niveladora"]),
    ("Mantenimiento preventivo", "MUERTO", ["Retroexcavadora", "Volteo"]),
    ("Mantenimiento correctivo", "MUERTO", ["Retroexcavadora", "Volteo"]),

    ("Mezcla de concreto", "PRODUCTIVO", ["Trompo"]),
    ("Transporte de concreto", "PRODUCTIVO", ["Trompo"]),

    ("Perforación de suelo", "PRODUCTIVO", ["Perforadora"]),
    ("Perforación de roca", "PRODUCTIVO", ["Perforadora"]),
]

# ============================
# IMPORTADOR
# ============================

def importar():
    print("🚀 Cargando actividades...")

    for nombre, tipo, tipos in DATA:

        actividad, created = ActividadEquipo.objects.get_or_create(
            nombre=nombre,
            defaults={"tipo": tipo}
        )

        # actualizar tipo si ya existe
        actividad.tipo = tipo
        actividad.save()

        # limpiar relaciones previas
        actividad.tipos_equipo.clear()

        for t in tipos:
            try:
                tipo_equipo = TipoEquipo.objects.get(nombre__iexact=t)
                actividad.tipos_equipo.add(tipo_equipo)
            except TipoEquipo.DoesNotExist:
                print(f"⚠️ TipoEquipo no existe: {t}")

        print(f"{'✔️ Creado' if created else '♻️ Actualizado'}: {nombre}")

    print("✅ Proceso terminado")


if __name__ == "__main__":
    importar()
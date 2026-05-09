import pandas as pd
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cobra.settings")
django.setup()

from adm.models import MantenimientoEquipo, Equipo, Proyecto

RUTA = "REPARACIONES.xlsx"


def importar():
    df = pd.read_excel(RUTA)

    print("📊 Columnas:", df.columns)
    print(f"📊 Filas: {len(df)}\n")

    ok = 0
    errores = 0

    for i, row in df.iterrows():
        try:
            # =========================
            # EQUIPO (desde "Máquina")
            # =========================
            equipo_id = row.get("Máquina")

            if pd.isna(equipo_id):
                print(f"⚠️ Fila {i}: sin equipo")
                continue

            equipo = Equipo.objects.filter(id=int(equipo_id)).first()

            if not equipo:
                print(f"⚠️ Fila {i}: equipo {equipo_id} no existe")
                continue

            # =========================
            # PROYECTO (desde "Lugar")
            # =========================
            nombre_proyecto = str(row.get("Lugar") or "").strip()

            proyecto = Proyecto.objects.filter(nombre__icontains=nombre_proyecto).first()

            # =========================
            # FECHA
            # =========================
            fecha = row.get("Fecha")
            if pd.notna(fecha):
                fecha = pd.to_datetime(fecha).date()
            else:
                print(f"⚠️ Fila {i}: sin fecha")
                continue

            # =========================
            # DESCRIPCIÓN
            # =========================
            descripcion = str(row.get("Reparación") or "").strip()

            if not descripcion:
                print(f"⚠️ Fila {i}: sin descripción")
                continue

            # =========================
            # COSTO
            # =========================
            costo = row.get("Precio")
            costo = float(costo) if pd.notna(costo) else 0

            # =========================
            # PROVEEDOR
            # =========================
            proveedor = str(row.get("Proveedor") or "").strip()

            # =========================
            # PRÓXIMO CAMBIO
            # =========================
            proximo = row.get("Próximo cambio")
            if pd.notna(proximo):
                proximo = pd.to_datetime(proximo).date()
            else:
                proximo = None

            # =========================
            # INSERT
            # =========================
            MantenimientoEquipo.objects.create(
                equipo=equipo,
                proyecto=proyecto,
                fecha=fecha,
                tipo="CORRECTIVO",
                descripcion=descripcion,
                proveedor=proveedor,
                costo=costo,
                proximo_cambio=proximo
            )

            print(f"✔ Fila {i}: OK")
            ok += 1

        except Exception as e:
            print(f"❌ Fila {i}: {e}")
            errores += 1
            continue

    print("\n====================")
    print(f"✔ Insertados: {ok}")
    print(f"❌ Errores: {errores}")
    print("====================")


if __name__ == "__main__":
    importar()
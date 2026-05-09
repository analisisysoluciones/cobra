import pandas as pd
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cobra.settings")
django.setup()

from adm.models import OrdenServicio, Equipo, Proyecto, Proveedor

RUTA = "REPARACIONES.xlsx"
HOJA = "Hoja 2"


def limpiar_texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def importar():
    df = pd.read_excel(RUTA, sheet_name=HOJA)

    print(f"📊 Filas encontradas: {len(df)}")

    creados = 0
    errores = 0
    omitidos = 0

    # ⚠️ proveedor fallback (CRÍTICO)
    proveedor_default = Proveedor.objects.first()

    if not proveedor_default:
        print("❌ No hay proveedores en la base. Crea uno antes.")
        return

    for i, row in df.iterrows():
        try:
            # ========================
            # EQUIPO
            # ========================
            equipo_id = row.get("Máquina")

            if pd.isna(equipo_id):
                omitidos += 1
                print(f"⚠️ Fila {i}: sin equipo")
                continue

            try:
                equipo = Equipo.objects.get(id=int(float(equipo_id)))
            except:
                omitidos += 1
                print(f"⚠️ Fila {i}: equipo inválido ({equipo_id})")
                continue

            # ========================
            # FECHA
            # ========================
            fecha = row.get("Fecha")

            if pd.isna(fecha):
                omitidos += 1
                print(f"⚠️ Fila {i}: sin fecha")
                continue

            # ========================
            # PROYECTO
            # ========================
            proyecto_nombre = limpiar_texto(row.get("Lugar"))

            proyecto = None
            if proyecto_nombre:
                proyecto = Proyecto.objects.filter(
                    nombre__icontains=proyecto_nombre
                ).first()

            # ========================
            # PROVEEDOR (FIX CRÍTICO)
            # ========================
            proveedor_nombre = limpiar_texto(row.get("Proveedor"))

            proveedor = None
            if proveedor_nombre:
                proveedor = Proveedor.objects.filter(
                    nombre__icontains=proveedor_nombre
                ).first()

            # 👉 fallback SIEMPRE válido
            if not proveedor:
                proveedor = proveedor_default

            # ========================
            # CAMPOS
            # ========================
            descripcion = limpiar_texto(row.get("Reparación"))
            responsable = limpiar_texto(row.get("Mecanic/Opera"))
            estado = limpiar_texto(row.get("Estado"))

            costo = row.get("Precio")
            if pd.isna(costo):
                costo = 0

            # ========================
            # DUPLICADOS (OPCIONAL PERO RECOMENDADO)
            # ========================
            existe = OrdenServicio.objects.filter(
                equipo=equipo,
                fecha=fecha,
                descripcion_falla=descripcion
            ).exists()

            if existe:
                omitidos += 1
                print(f"⚠️ Fila {i}: duplicada")
                continue

            # ========================
            # INSERT
            # ========================
            OrdenServicio.objects.create(
                fecha=fecha,
                equipo=equipo,
                proveedor=proveedor,
                proyecto=proyecto,
                tipo_servicio='COR',
                descripcion_falla=descripcion,
                estatus='CERRADA',
                observaciones="Importado desde Excel",
                costo=costo,
                responsable=responsable,
                estado=estado,
            )

            creados += 1
            print(f"✔ Fila {i} importada")

        except Exception as e:
            errores += 1
            print(f"❌ Error en fila {i}: {e}")
            continue

    print("\n==============================")
    print(f"✅ Registros creados: {creados}")
    print(f"⚠️ Omitidos: {omitidos}")
    print(f"❌ Errores: {errores}")
    print("==============================")


if __name__ == "__main__":
    importar()
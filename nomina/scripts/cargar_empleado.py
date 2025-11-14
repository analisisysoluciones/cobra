import os
import django
from datetime import datetime, date
import pandas as pd

# Configurar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cobra.settings')
django.setup()

from nomina.models import Empleado

# Ruta del archivo CSV
archivo_csv = r"C:\proyectos\cobra\cobra\nomina\scripts\EMPLEADOS.csv"

# Leer CSV (con codificación correcta para acentos y ñ)
df = pd.read_csv(archivo_csv, encoding="latin1")
df.columns = [c.strip().upper() for c in df.columns]  # Normalizar encabezados

# Detectar columnas relevantes
col_codigo = next((c for c in df.columns if "COD" in c), None)
col_nombre = next((c for c in df.columns if "NOMBRE" in c), None)
col_sueldo = next((c for c in df.columns if "SUELDO" in c), None)
col_comp = next((c for c in df.columns if "COMP" in c), None)

base_curp = "AAAA000000XXXX"
usuario_id = 1  # Usuario que crea/modifica

for i, fila in df.iterrows():
    # Código tomado directamente del archivo CSV
    codigo = int(fila[col_codigo]) if col_codigo and not pd.isna(fila[col_codigo]) else i + 1

    nombre = str(fila[col_nombre]).strip().upper() if col_nombre else f"EMPLEADO {i+1}"
    rfc = f"RFC{codigo:04d}"
    curp = f"{base_curp}{codigo:02d}"

    # Sueldo y compensación (si existen en el CSV)
    sueldo_diario = float(fila[col_sueldo]) if col_sueldo and not pd.isna(fila[col_sueldo]) else 0.00
    compensacion = float(fila[col_comp]) if col_comp and not pd.isna(fila[col_comp]) else 0.00

    empleado = Empleado(
        codigo=codigo,
        curp=curp,
        rfc=rfc,
        nombre=nombre,
        ingreso=date.today(),
        sueldo_diario=sueldo_diario,
        compensacion=compensacion,
        puesto="AUXILIAR GENERAL",
        estado=True,
        uc_id=usuario_id,
        um=usuario_id,
        fc=datetime.now(),
        fm=datetime.now(),
    )

    try:
        empleado.save()
        print(f"✅ {codigo} - {nombre} | Sueldo: ${sueldo_diario:.2f} | Comp: ${compensacion:.2f}")
    except Exception as e:
        print(f"⚠️ Error con {nombre} (Código {codigo}): {e}")

print(f"\nProceso completado. Total empleados procesados: {len(df)}")

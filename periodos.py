import os
import django
import pandas as pd
from datetime import datetime

# Inicializar entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cobra.settings')
django.setup()

from nomina.models import PeriodosNomina  # Ajusta el import si tu app tiene otro nombre

# Ruta del archivo CSV que deseas importar
ARCHIVO_CSV = 'periodos_nomina_2025_completo.csv'  # Debe estar junto a manage.py

def importar_periodos():
    print("=== CARGA DE PERIODOS DE NOMINA ===")
    try:
        df = pd.read_csv(ARCHIVO_CSV)
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return

    nuevos, actualizados, existentes = 0, 0, 0

    for _, fila in df.iterrows():
        try:
            anio = int(fila['anio'])
            semana = int(fila['semana'])
            inicio = datetime.strptime(str(fila['inicio']), "%d/%m/%Y").date()
            fin = datetime.strptime(str(fila['fin']), "%d/%m/%Y").date()
            incidencia = datetime.strptime(str(fila['incidencia']), "%d/%m/%Y").date()
            pago = datetime.strptime(str(fila['pago']), "%d/%m/%Y").date()

            periodo, creado = PeriodosNomina.objects.get_or_create(
                anio=anio,
                semana=semana,
                defaults={
                    'periodo_inicio': inicio,
                    'periodo_final': fin,
                    'fecha_corte': incidencia,
                    'dia_pago': pago,
                    'estatus': 'ABIERTO',
                }
            )

            if not creado:
                # Si ya existe, validamos si cambió algo
                cambios = False
                if (periodo.periodo_inicio != inicio or
                    periodo.periodo_final != fin or
                    periodo.fecha_corte != incidencia or
                    periodo.dia_pago != pago):
                    periodo.periodo_inicio = inicio
                    periodo.periodo_final = fin
                    periodo.fecha_corte = incidencia
                    periodo.dia_pago = pago
                    periodo.save()
                    cambios = True
                    actualizados += 1
                else:
                    existentes += 1
            else:
                nuevos += 1

        except Exception as e:
            print(f"⚠️ Error en fila {fila.to_dict()}: {e}")

    print(f"\n✅ Carga completada.")
    print(f"📦 Nuevos: {nuevos}")
    print(f"🔄 Actualizados: {actualizados}")
    print(f"⏸ Existentes sin cambios: {existentes}")

if __name__ == "__main__":
    importar_periodos()

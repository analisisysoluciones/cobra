from datetime import date, timedelta
from django.db import transaction
from nomina.models import PeriodosNomina


@transaction.atomic
def generar_periodos_nomina_2026():
    
    # 🔴 BORRAR TODO (porque tú mismo lo decidiste)
    PeriodosNomina.objects.all().delete()

    inicio = date(2025, 12, 29)  # lunes base real
    semana = 1
    registros = []

    while True:
        fin = inicio + timedelta(days=6)

        # detener cuando ya no toque 2026
        if fin.year > 2026:
            break

        # jueves dentro del periodo
        fecha_corte = inicio + timedelta(days=3)

        # sábado (2 días después del corte)
        dia_pago = fecha_corte + timedelta(days=2)

        registros.append(
            PeriodosNomina(
                anio=fin.year,
                semana=semana,
                periodo_inicio=inicio,
                periodo_final=fin,
                fecha_corte=fecha_corte,
                dia_pago=dia_pago,
                estatus='ABIERTO'
            )
        )

        inicio = fin + timedelta(days=1)
        semana += 1

    # inserción masiva (rápida y limpia)
    PeriodosNomina.objects.bulk_create(registros)

    print(f"✔ Periodos generados: {len(registros)}")
from .models import IngresoExtraordinario
from django.db.models import Sum

def filtrar_ingresos(request, form):
    qs = IngresoExtraordinario.objects.all().order_by("-fecha")

    if form.is_valid():
        fecha_inicio = form.cleaned_data.get("fecha_inicio")
        fecha_fin = form.cleaned_data.get("fecha_fin")
        proyecto = form.cleaned_data.get("proyecto")
        cuenta = form.cleaned_data.get("cuenta")
        tipo = form.cleaned_data.get("tipo")

        if fecha_inicio:
            qs = qs.filter(fecha__gte=fecha_inicio)

        if fecha_fin:
            qs = qs.filter(fecha__lte=fecha_fin)

        if proyecto:
            qs = qs.filter(proyecto=proyecto)

        if cuenta:
            qs = qs.filter(cuenta=cuenta)

        if tipo:
            qs = qs.filter(tipo=tipo)

    return qs

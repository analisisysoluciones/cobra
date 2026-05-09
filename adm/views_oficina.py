from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import ReporteEquipoDetalle
from django.utils.dateparse import parse_date
from .utils import es_admin


@login_required
def oficina_actividades(request):

    if not es_admin(request.user):
        return render(request, "base/403.html")

    qs = ReporteEquipoDetalle.objects.select_related(
        "usuario", "actividad", "reporte"
    ).order_by("-creado")

    # 🔍 filtros
    operador = request.GET.get("operador")
    fecha = request.GET.get("fecha")

    if operador:
        qs = qs.filter(usuario_id=operador)

    if fecha:
        fecha = parse_date(fecha)
        if fecha:
            qs = qs.filter(creado__date=fecha)

    return render(request, "adm/oficina_actividades.html", {
        "datos": qs
    })


from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.utils import timezone
from .forms import ActividadDetalleForm


@login_required
def editar_actividad(request, pk):

    obj = get_object_or_404(ReporteEquipoDetalle, pk=pk)

    if not es_admin(request.user):
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        form = ActividadDetalleForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)

            # 🔥 auditoría
            obj.editado_por = request.user
            obj.editado_en = timezone.now()

            obj.save()
            return redirect("adm:oficina_actividades")

    else:
        form = ActividadDetalleForm(instance=obj)

    if form.is_valid():
        obj = form.save(commit=False)

        if obj.inicio_dt and obj.fin_dt:
            delta = obj.fin_dt - obj.inicio_dt
            obj.horas = round(delta.total_seconds() / 3600, 2)

        obj.editado_por = request.user
        obj.editado_en = timezone.now()
        obj = form.save(commit=False)


        obj.save()

    return render(request, "adm/editar_actividad.html", {
        "form": form
    })    
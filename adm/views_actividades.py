# adm/views_actividades.py (recomendado separarlo)

from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import TipoEquipo, ActividadEquipo
from .forms import TipoEquipoForm, ActividadEquipoForm
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.utils import timezone

# ======================
# TIPO EQUIPO
# ======================

class TipoEquipoListView(ListView):
    model = TipoEquipo
    template_name = "adm/tipo_equipo_list.html"
    context_object_name = "objetos"


class TipoEquipoCreateView(CreateView):
    model = TipoEquipo
    form_class = TipoEquipoForm
    template_name = "adm/tipo_equipo_form.html"
    success_url = reverse_lazy('adm:tipo_equipo_list')


class TipoEquipoUpdateView(UpdateView):
    model = TipoEquipo
    form_class = TipoEquipoForm
    template_name = "adm/tipo_equipo_form.html"
    success_url = reverse_lazy('adm:tipo_equipo_list')


class TipoEquipoDeleteView(DeleteView):
    model = TipoEquipo
    template_name = "adm/confirm_delete.html"
    success_url = reverse_lazy('adm:tipo_equipo_list')


# ======================
# ACTIVIDADES
# ======================

class ActividadEquipoListView(ListView):
    model = ActividadEquipo
    template_name = "adm/actividad_list.html"
    context_object_name = "objetos"

    def get_queryset(self):
        return ActividadEquipo.objects.prefetch_related('tipos_equipo')


class ActividadEquipoCreateView(CreateView):
    model = ActividadEquipo
    form_class = ActividadEquipoForm
    template_name = "adm/actividad_form.html"
    success_url = reverse_lazy('adm:actividad_list')


class ActividadEquipoUpdateView(UpdateView):
    model = ActividadEquipo
    form_class = ActividadEquipoForm
    template_name = "adm/actividad_form.html"
    success_url = reverse_lazy('adm:actividad_list')


class ActividadEquipoDeleteView(DeleteView):
    model = ActividadEquipo
    template_name = "adm/actividad_confirm_delete.html"
    success_url = reverse_lazy('adm:actividad_list')





def iniciar_actividad(request):
    print("BODY:", request.body) 
    data = json.loads(request.body or "{}")
    print("DATA:", data)
    print("ACTIVIDAD_ID:", data.get("actividad_id"))

    data = json.loads(request.body or "{}")

    actividad_id = data.get("actividad_id")
    proyecto_id = data.get("proyecto_id")

    if not actividad_id:
        return JsonResponse({
            "ok": False,
            "msg": "No viene actividad_id"
        })

    actividad = Actividad.objects.get(id=actividad_id)

    jornada = ReporteEquipoPDA.objects.filter(
        usuario=request.user,
        estatus="ABIERTA"
    ).order_by("-inicio").first()

    if not jornada:
        return JsonResponse({"ok": False, "msg": "No hay jornada activa"})

    if not proyecto_id:
        return JsonResponse({"ok": False, "msg": "Proyecto requerido"})

    # 🔥 cerrar actividad anterior
    actividad_abierta = ReporteEquipoDetalle.objects.filter(
        reporte=jornada,
        fin__isnull=True
    ).first()

    if actividad_abierta:
        actividad_abierta.fin = timezone.now()
        actividad_abierta.horas = (
            actividad_abierta.fin - actividad_abierta.inicio
        ).total_seconds() / 3600
        actividad_abierta.save()

    # 🔥 crear nueva
    ReporteEquipoDetalle.objects.create(
        reporte=jornada,
        usuario=request.user,
        actividad=actividad,
        proyecto_id=proyecto_id,
        inicio=timezone.now(),
        origen="OPERADOR"
    )

    return JsonResponse({
        "ok": True,
        "actividad_actual": actividad.nombre
    })
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import RentaEquipo, Cliente, TarifaEquipo
from .forms import RentaEquipoForm, ClienteForm, TarifaEquipoForm
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.utils import timezone
from django.db.models import Sum


class RentaEquipoCreateView(CreateView):
    model = RentaEquipo
    form_class = RentaEquipoForm
    template_name = "renta/renta_form.html"
    success_url = reverse_lazy("renta:renta_list")

class RentaEquipoListView(ListView):
    model = RentaEquipo
    template_name = "renta/renta_list.html"
    context_object_name = "rentas"

    def get_queryset(self):
        return RentaEquipo.objects.select_related(
            "cliente", "equipo", "tarifa"
        ).order_by("-creado")    



def reporte_rentas(request):

    total = RentaEquipo.objects.aggregate(
        total=Sum("importe")
    )["total"] or 0

    por_cliente = RentaEquipo.objects.values("cliente__nombre")\
        .annotate(total=Sum("importe"))\
        .order_by("-total")

    return render(request, "renta/reporte_rentas.html", {
        "total": total,
        "por_cliente": por_cliente
    })        


class ClienteListView(ListView):
    model = Cliente
    template_name = "renta/cliente_list.html"
    context_object_name = "clientes"


class ClienteCreateView(CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "renta/cliente_form.html"
    success_url = reverse_lazy("renta:cliente_list")


class ClienteUpdateView(UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "renta/cliente_form.html"
    success_url = reverse_lazy("renta:cliente_list")            


class TarifaEquipoListView(ListView):
    model = TarifaEquipo
    template_name = "renta/tarifa_list.html"
    context_object_name = "tarifas"

    def get_queryset(self):
        return TarifaEquipo.objects.select_related("equipo").order_by("-id")

class TarifaEquipoCreateView(CreateView):
    model = TarifaEquipo
    form_class = TarifaEquipoForm
    template_name = "renta/tarifa_form.html"
    success_url = reverse_lazy("renta:tarifa_list")


class TarifaEquipoUpdateView(UpdateView):
    model = TarifaEquipo
    form_class = TarifaEquipoForm
    template_name = "renta/tarifa_form.html"
    success_url = reverse_lazy("renta:tarifa_list")



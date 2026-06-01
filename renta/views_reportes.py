from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from .models import RentaConcepto, RentaEquipo, Cliente, ConceptoRentaCatalogo
from adm.models import Equipo

class ReporteRentasActivasView(
    LoginRequiredMixin,
    ListView
):

    model = RentaEquipo

    template_name = (
        "renta/reportes/rentas_activas.html"
    )

    context_object_name = "rentas"


    def get_queryset(self):

        qs = (

            RentaEquipo.objects

            .filter(
                estatus="ACTIVA"
            )

            .select_related(
                "cliente",
                "equipo",
                "tarifa"
            )

            .order_by(
                "-fecha_inicio"
            )

        )

        cliente = self.request.GET.get(
            "cliente"
        )

        equipo = self.request.GET.get(
            "equipo"
        )

        if cliente:

            qs = qs.filter(
                cliente_id=cliente
            )

        if equipo:

            qs = qs.filter(
                equipo_id=equipo
            )

        return qs


    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        context["clientes"] = (
            Cliente.objects
            .filter(activo=True)
            .order_by("nombre")
        )

        context["equipos"] = (
            Equipo.objects
            .filter(estado=True)
            .order_by("descripcion")
        )

        return context
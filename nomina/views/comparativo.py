from django.views.generic import TemplateView
from django.shortcuts import render
from .forms_reporte_comparativo import NominaComparativoFiltroForm
from .utils_comparativos import (
    comparar_semanas,
    comparar_meses,
    comparar_proyectos
)


class NominaComparativoView(TemplateView):
    template_name = "nomina/comparativo.html"

    def get(self, request, *args, **kwargs):

        form = NominaComparativoFiltroForm(request.GET or None)
        resultados = []

        if form.is_valid():
            tipo = form.cleaned_data["tipo"]
            anio = form.cleaned_data["anio"]
            proyecto = form.cleaned_data["proyecto"]

            if tipo == "SEMANAL":
                resultados = comparar_semanas(anio, proyecto)

            elif tipo == "MENSUAL":
                resultados = comparar_meses(anio, proyecto)

            elif tipo == "PROYECTOS":
                resultados = comparar_proyectos(anio)

        ctx = {
            "form": form,
            "resultados": resultados,
        }
        return render(request, self.template_name, ctx)
    


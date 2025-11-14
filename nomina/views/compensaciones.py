from django.views import generic
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from nomina.models import CompensacionVariable, Empleado
from nomina.forms import CompensacionVariableForm


class CompensacionVariableListView(LoginRequiredMixin, generic.ListView):
    model = CompensacionVariable
    template_name = "nomina/compensacion_variable_list.html"
    context_object_name = "compensaciones"
    paginate_by = 20
    ordering = ["-fecha"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("empleado", "periodo")
        empleado = self.request.GET.get("empleado")
        periodo = self.request.GET.get("periodo")
        if empleado:
            qs = qs.filter(empleado__nombre__icontains=empleado)
        if periodo:
            qs = qs.filter(periodo__id=periodo)
        return qs


class CompensacionVariableCreateView(LoginRequiredMixin, generic.CreateView):
    model = CompensacionVariable
    form_class = CompensacionVariableForm
    template_name = "nomina/compensacion_variable_form.html"

    def get_initial(self):
        return {"empleado": get_object_or_404(Empleado, pk=self.kwargs["empleado_id"])}

    def get_success_url(self):
        return reverse("nom:empleado_list")

class CompensacionVariableUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = CompensacionVariable
    form_class = CompensacionVariableForm
    template_name = "nomina/compensacion_variable_form.html"
    success_url = reverse_lazy("nom:compensacion_variable_list")

    def form_valid(self, form):
        messages.success(self.request, "✅ Compensación actualizada correctamente.")
        return super().form_valid(form)


class CompensacionVariableDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = CompensacionVariable
    template_name = "nomina/compensacion_variable_confirm_delete.html"
    success_url = reverse_lazy("nom:compensacion_variable_list")

    def delete(self, request, *args, **kwargs):
        messages.warning(self.request, "❌ Compensación eliminada correctamente.")
        return super().delete(request, *args, **kwargs)

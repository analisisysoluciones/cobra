from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from nomina.models import PerfilPuesto
from nomina.forms import PerfilPuestoForm


class PerfilListView(ListView):
    model = PerfilPuesto
    template_name = 'nomina/perfil_list.html'
    context_object_name = 'perfiles'

    def get_queryset(self):
        return PerfilPuesto.objects.all().order_by('categoria', 'nombre')


class PerfilCreateView(CreateView):
    model = PerfilPuesto
    form_class = PerfilPuestoForm
    template_name = 'nomina/perfil_form.html'
    success_url = reverse_lazy('nom:perfil_list')


class PerfilUpdateView(UpdateView):
    model = PerfilPuesto
    form_class = PerfilPuestoForm
    template_name = 'nomina/perfil_form.html'
    success_url = reverse_lazy('nom:perfil_list')


class PerfilDeleteView(DeleteView):
    model = PerfilPuesto
    template_name = 'nomina/perfil_confirm_delete.html'
    success_url = reverse_lazy('nom:perfil_list')
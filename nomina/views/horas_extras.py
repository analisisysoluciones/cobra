from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.views import generic,View
from django.contrib.auth.decorators import login_required
from ..models import HorasExtras, Empleado
from ..forms import HorasExtrasForm

@login_required(login_url='bases:login')
def horas_extras_list(request):
    horas = HorasExtras.objects.select_related('empleado', 'periodo').order_by('-fecha')
    return render(request, 'nomina/horas_extras_list.html', {'horas': horas})


@login_required(login_url='bases:login')
def horas_extras_new(request):
    if request.method == "POST":
        form = HorasExtrasForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Horas extra registradas correctamente.")
            return redirect('nom:horas_extras_list')
        else:
            messages.error(request, "Verifique los datos del formulario.")
    else:
        form = HorasExtrasForm()

    return render(request, 'nomina/horas_extras_form.html', {'form': form})


class HorasExtrasEmpleadoCreateView(generic.CreateView):
    model = HorasExtras
    form_class = HorasExtrasForm
    template_name = "nomina/horas_extras_form.html"

    def get_initial(self):
        return {"empleado": get_object_or_404(Empleado, pk=self.kwargs["empleado_id"])}

    def get_success_url(self):
        return reverse("nom:empleado_list")
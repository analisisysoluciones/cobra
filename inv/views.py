from django.shortcuts import render
from django.views import generic
from django.urls import reverse_lazy
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Categoria, Material, Unidad
from .forms import CategoriaForm, MaterialForm, UnidadForm
from django.contrib.messages.views import SuccessMessageMixin
from bases.views import SinPrivilegios
# Create your views here.



class CategoriaView(LoginRequiredMixin, SinPrivilegios, generic.ListView):
    permission_required='inv.view_categoria'
    model = Categoria
    template_name="inv/categoria_list.html"
    context_object_name = "obj"
    login_url = "bases:login"

class CategoriaNew(LoginRequiredMixin, generic.CreateView):
    model = Categoria
    template_name="inv/categoria_form.html"
    context_object_name = "obj"
    form_class = CategoriaForm
    success_url = reverse_lazy("inv:categoria_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.uc = self.request.user
        return super().form_valid(form)


class CategoriaEdit(LoginRequiredMixin, generic.UpdateView):
    model = Categoria
    template_name="inv/categoria_form.html"
    context_object_name = "obj"
    form_class = CategoriaForm
    success_url = reverse_lazy("inv:categoria_list")
    login_url = "bases:login"

    def form_valid(self, form):
        form.instance.um = self.request.user.id
        return super().form_valid(form)

class CategoriaDel(LoginRequiredMixin, generic.DeleteView):
    model = Categoria
    template_name='inv/categoria_del.html'
    context_object_name='obj'
    success_url=reverse_lazy('inv:categoria_list')
    
#==========================================================================#
#==========================================================================#
#==========================================================================#


# Vistas para Unidad
class UnidadView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "inv.view_unidad"
    model = Unidad
    template_name = "inv/unidad_list.html"
    context_object_name = "unidades"
    login_url = "bases:login"

class UnidadNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Unidad
    template_name = "inv/unidad_form.html"
    context_object_name = "unidad"
    form_class = UnidadForm
    success_url = reverse_lazy("inv:unidad_list")
    login_url = "bases:login"
    success_message='Unidad capturada satifactoriamente'

    def form_valid(self, form):
        # Aquí puedes añadir lógica adicional si es necesario
        return super().form_valid(form)

class UnidadEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Unidad
    template_name = "inv/unidad_form.html"
    context_object_name = "obj"
    form_class = UnidadForm
    success_url = reverse_lazy("inv:unidad_list")
    login_url = "bases:login"
    success_message='Unidad actualizada satifactoriamente'

    def form_valid(self, form):
        # Aquí puedes añadir lógica adicional si es necesario
        return super().form_valid(form)
    
class UnidadDel(LoginRequiredMixin, generic.DeleteView):
    model = Unidad
    template_name='inv/unidad_del.html'
    context_object_name='obj'
    success_url=reverse_lazy('inv:unidad_list')
    



# Vistas para Material
class MaterialView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    permission_required = "inv.view_material"
    model = Material
    template_name = "inv/material_list.html"
    context_object_name = "materiales"
    login_url = "bases:login"
    

class MaterialNew(SuccessMessageMixin, LoginRequiredMixin, generic.CreateView):
    model = Material
    template_name = "inv/material_form.html"
    context_object_name = "material"
    form_class = MaterialForm
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"
    success_message='Material capturado satifactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = Unidad.objects.all()  # Pasar todas las unidades
        return context

    def form_valid(self, form):
        form.instance.uc = self.request.user  # Asigna el usuario creador
        return super().form_valid(form)

class MaterialEdit(SuccessMessageMixin, LoginRequiredMixin, generic.UpdateView):
    model = Material
    template_name = "inv/material_form.html"
    context_object_name = "obj"
    form_class = MaterialForm
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"
    success_message='Material actualizado satifactoriamente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unidades'] = Unidad.objects.all()  # Pasar todas las unidades
        return context

    def form_valid(self, form):
        form.instance.um = self.request.user.id  # Asigna el usuario que modifica
        return super().form_valid(form)


class MaterialDel(LoginRequiredMixin, generic.DeleteView):
    model = Material
    template_name = "inv/material_del.html"
    context_object_name = "obj"
    success_url = reverse_lazy("inv:material_list")
    login_url = "bases:login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Eliminar Material"
        return context


def generar_reporte_materiales(request):
    materiales = Material.objects.prefetch_related('unidad_medida').all()
    
    html_string = render_to_string('inv/material_report.html', {'materiales': materiales})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_materiales.pdf"'
    
    # Convertir HTML a PDF
    pisa_status = pisa.CreatePDF(html_string, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: {}'.format(pisa_status.err))
    
    return response




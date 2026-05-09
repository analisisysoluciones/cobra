from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import generic
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView


# Create your views here.
class SinPrivilegios(PermissionRequiredMixin):
     raise_exception=False
     redirect_field_name='redirect_to'

     def handle_no_permission(self):
          from django.contrib.auth.models import AnonymousUser
          if not self.request.user==AnonymousUser():
               self.login_url='bases:sin_privilegios'
          return HttpResponseRedirect(reverse_lazy(self.login_url))

class Home(LoginRequiredMixin,generic.TemplateView):
    template_name='bases/home.html'
    login_url = 'bases:login'

class HomeSinPrivilegios(generic.TemplateView):
      template_name="bases/sin_privilegios.html"



class CobraLoginView(LoginView):
    template_name = "bases/login.html"

    def get_success_url(self):

        user = self.request.user

        if user.is_superuser:
            return reverse_lazy("bases:home")

        if user.groups.filter(name="Operadores").exists():
            return reverse_lazy("adm:pda_menu")

        return reverse_lazy("bases:home")      
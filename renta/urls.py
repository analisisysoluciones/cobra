from django.urls import path
from .views import(
    RentaEquipoCreateView, RentaEquipoListView, reporte_rentas, ClienteCreateView, ClienteListView, ClienteUpdateView,
    TarifaEquipoCreateView, TarifaEquipoListView, TarifaEquipoUpdateView
    
) 


app_name = 'renta'

urlpatterns = [

    path("rentas/", RentaEquipoListView.as_view(), name="renta_list"),
    path("rentas/nuevo/", RentaEquipoCreateView.as_view(), name="renta_new"),
    path("rentas/reporte/", reporte_rentas, name="renta_reporte"),
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", ClienteCreateView.as_view(), name="cliente_new"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente_edit"),
    path("tarifas/", TarifaEquipoListView.as_view(), name="tarifa_list"),
    path("tarifas/nuevo/", TarifaEquipoCreateView.as_view(), name="tarifa_new"),
    path("tarifas/<int:pk>/editar/", TarifaEquipoUpdateView.as_view(), name="tarifa_edit"),
]

from django.urls import path
from .views import(
    RentaEquipoCreateView, RentaEquipoListView, reporte_rentas, ClienteCreateView, ClienteListView, ClienteUpdateView,
    TarifaEquipoCreateView, TarifaEquipoListView, TarifaEquipoUpdateView, cliente_ajax_crear, RentaEquipoDetailView,
    RentaEquipoUpdateView, finalizar_renta, cancelar_renta, renta_pdf, PagoRentaCreateView
    
) 


app_name = 'renta'

urlpatterns = [

    path("rentas/", RentaEquipoListView.as_view(), name="renta_list"),
    path("rentas/nuevo/", RentaEquipoCreateView.as_view(), name="renta_new"),
    path("rentas/reporte/", reporte_rentas, name="renta_reporte"),
    path("rentas/<int:pk>/editar/",RentaEquipoUpdateView.as_view(),name="renta_update"),
    path("rentas/<int:pk>/",RentaEquipoDetailView.as_view(), name="renta_detail"),
    path("rentas/<int:pk>/finalizar/",finalizar_renta,name="renta_finalizar"),
    path("rentas/<int:pk>/cancelar/",cancelar_renta,name="renta_cancelar"),
    path("rentas/<int:pk>/pdf/",renta_pdf,name="renta_pdf"),
    path("rentas/<int:pk>/pago/",PagoRentaCreateView.as_view(),name="pago_create"),
    
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", ClienteCreateView.as_view(), name="cliente_new"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente_edit"),
    path("clientes/ajax/crear/",cliente_ajax_crear, name="cliente_ajax_crear"),
    
    path("tarifas/", TarifaEquipoListView.as_view(), name="tarifa_list"),
    path("tarifas/nuevo/", TarifaEquipoCreateView.as_view(), name="tarifa_new"),
    path("tarifas/<int:pk>/editar/", TarifaEquipoUpdateView.as_view(), name="tarifa_edit"),
    
    
]

from django.urls import path
from .views import(
    RentaEquipoCreateView, RentaEquipoListView, reporte_rentas, ClienteCreateView, ClienteListView, ClienteUpdateView,
    TarifaEquipoCreateView, TarifaEquipoListView, TarifaEquipoUpdateView, cliente_ajax_crear, RentaEquipoDetailView,
    RentaEquipoUpdateView, finalizar_renta, cancelar_renta, renta_pdf, PagoRentaCreateView, RentaConcepto, ConceptoRentaCatalogoCreateView,
    ConceptoRentaCatalogoListView,ConceptoRentaCatalogoUpdateView, concepto_precio_ajax, ConvertirRentaView, PagoRapidoView,
    FinalizarRentaView, ReciboPagoView
) 

from renta.views_reportes import *

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
    
    path("reportes/",ReporteRentasActivasView.as_view(),name="reportes_renta_activas"),
    
    path("catalogos/conceptos/",ConceptoRentaCatalogoListView.as_view(),name="concepto_list"),

    path("catalogos/conceptos/nuevo/",ConceptoRentaCatalogoCreateView.as_view(),name="concepto_create"),
    path("catalogos/conceptos/<int:pk>/editar/",ConceptoRentaCatalogoUpdateView.as_view(),name="concepto_update"),    
    path("conceptos/<int:pk>/precio/",concepto_precio_ajax,name="concepto_precio_ajax"),
    path("rentas/<int:pk>/convertir/",ConvertirRentaView.as_view(),name="convertir_renta"),
    
    path("rentas/<int:pk>/pago/",      PagoRapidoView.as_view(),   name="pago_rapido"),
    path("rentas/<int:pk>/finalizar/", FinalizarRentaView.as_view(), name="finalizar_renta"),
    path("pagos/<int:pago_pk>/recibo/", ReciboPagoView.as_view(),   name="recibo_pago"),
    
]

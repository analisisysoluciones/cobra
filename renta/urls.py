from django.urls import path
from .views import(
    RentaEquipoCreateView, RentaEquipoListView, reporte_rentas, ClienteCreateView, ClienteListView, ClienteUpdateView,
    TarifaEquipoCreateView, TarifaEquipoListView, TarifaEquipoUpdateView, cliente_ajax_crear, RentaEquipoDetailView,
    RentaEquipoUpdateView, renta_pdf, RentaConcepto, ConceptoRentaCatalogoCreateView,
    ConceptoRentaCatalogoListView,ConceptoRentaCatalogoUpdateView, concepto_precio_ajax, ConvertirRentaView, PagoRapidoView,
    FinalizarRentaView, ReciboPagoView, cotizacion_pdf, CancelarRentaView
) 

from renta.views_reportes import *

app_name = 'renta'

urlpatterns = [

    path("rentas/", RentaEquipoListView.as_view(), name="renta_list"),
    path("rentas/nuevo/", RentaEquipoCreateView.as_view(), name="renta_new"),
    path("rentas/reporte/", reporte_rentas, name="renta_reporte"),
    path("rentas/<int:pk>/editar/", RentaEquipoUpdateView.as_view(), name="renta_update"),
    path("rentas/<int:pk>/", RentaEquipoDetailView.as_view(), name="renta_detail"),
    path("rentas/<int:pk>/pdf/", renta_pdf, name="renta_pdf"),
    path("rentas/<int:pk>/cotizacion/pdf/", cotizacion_pdf, name="cotizacion_pdf"),
    path("rentas/<int:pk>/convertir/", ConvertirRentaView.as_view(), name="convertir_renta"),

    # ── Pago, finalizar, cancelar — solo las versiones nuevas ──
    path("rentas/<int:pk>/pago/", PagoRapidoView.as_view(), name="pago_rapido"),
    path("rentas/<int:pk>/finalizar/", FinalizarRentaView.as_view(), name="finalizar_renta"),
    path("rentas/<int:pk>/cancelar/", CancelarRentaView.as_view(), name="cancelar_renta"),
    path("pagos/<int:pago_pk>/recibo/", ReciboPagoView.as_view(), name="recibo_pago"),

    # ── Clientes ──
    path("clientes/", ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", ClienteCreateView.as_view(), name="cliente_new"),
    path("clientes/<int:pk>/editar/", ClienteUpdateView.as_view(), name="cliente_edit"),
    path("clientes/ajax/crear/", cliente_ajax_crear, name="cliente_ajax_crear"),

    # ── Tarifas ──
    path("tarifas/", TarifaEquipoListView.as_view(), name="tarifa_list"),
    path("tarifas/nuevo/", TarifaEquipoCreateView.as_view(), name="tarifa_new"),
    path("tarifas/<int:pk>/editar/", TarifaEquipoUpdateView.as_view(), name="tarifa_edit"),

    # ── Catálogos ──
    path("catalogos/conceptos/", ConceptoRentaCatalogoListView.as_view(), name="concepto_list"),
    path("catalogos/conceptos/nuevo/", ConceptoRentaCatalogoCreateView.as_view(), name="concepto_create"),
    path("catalogos/conceptos/<int:pk>/editar/", ConceptoRentaCatalogoUpdateView.as_view(), name="concepto_update"),
    path("conceptos/<int:pk>/precio/", concepto_precio_ajax, name="concepto_precio_ajax"),

    # ── Reportes ──
    path("reportes/", ReporteRentasActivasView.as_view(), name="reportes_renta_activas"),
]
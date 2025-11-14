from django.urls import path
from .views import (
    IngresoExtraListView,
    IngresoExtraCreateView,
    IngresoExtraDetailView,
    IngresoExtraDeleteView,
    IngresoExtraReporteView,
    reporte_ingresos_excel,
    reporte_ingresos_pdf,
    afectar_ingreso_extra
)

app_name = "finanzas"

urlpatterns = [
    path("ingresos/", IngresoExtraListView.as_view(), name="ingreso_list"),
    path("ingresos/nuevo/", IngresoExtraCreateView.as_view(), name="ingreso_nuevo"),
    path("ingresos/<int:pk>/", IngresoExtraDetailView.as_view(), name="ingreso_detalle"),
    path("ingresos/<int:pk>/eliminar/", IngresoExtraDeleteView.as_view(), name="ingreso_eliminar"),
    path("ingresos/reporte/", IngresoExtraReporteView.as_view(), name="ingreso_reporte"),
    path("ingresos/reporte/pdf/", reporte_ingresos_pdf, name="ingreso_reporte_pdf"),
    path("ingresos/reporte/excel/", reporte_ingresos_excel, name="ingreso_reporte_excel"),
    path("ingresos/<int:pk>/afectar/", afectar_ingreso_extra, name="ingreso_afectar"),
    


]

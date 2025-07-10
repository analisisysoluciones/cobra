from django.urls import path
from . import views
from .views import(
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView, 
    ComprasView, compras,   
    CompraDetDelete, imprime_compra, subir_archivo_pdf, subir_evidencia_recoge, subir_evidencia_uso, subir_todos_los_archivos,
    compras_add_detalle_view, reporte_compras
) 



app_name = 'cxp'

urlpatterns = [
    
    path('proveedor', ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedor/new/', ProveedorCreateView.as_view(), name='proveedor_new'),
    path('proveedor/edit/<int:pk>/', ProveedorUpdateView.as_view(), name='proveedor_edit'),
    path('proveedor/delete/<int:pk>/', ProveedorDeleteView.as_view(), name='proveedor_del'),

    path('compras',ComprasView.as_view(), name="compras_list"),
    path('compras/new',compras, name="compras_new"),
    path('compras/edit/<int:compra_id>',compras, name="compras_edit"),
    path('compras/<int:compra_id>/delete/<int:pk>', CompraDetDelete.as_view(), name="compras_del"),
    path('imprime-compra/<int:compra_id>/', imprime_compra, name='imprime_compra'),

    path('compra/<int:compra_id>/subir-archivo/', views.subir_archivo_pdf, name='subir_archivo_pdf'),
    path('compra/<int:compra_id>/subir-evidencia-recoge/', views.subir_evidencia_recoge, name='subir_evidencia_recoge'),
    path('compra/<int:compra_id>/subir-evidencia-uso/', views.subir_evidencia_uso, name='subir_evidencia_uso'),
    path('compra/<int:compra_id>/subir-todos/', views.subir_todos_los_archivos, name='subir_todos_los_archivos'),
    path('compras/<int:compra_id>/add-detalle/', views.compras_add_detalle_view, name='compras_add_detalle'),
    path('reporte-compras/', reporte_compras, name='reporte_compras'),


   
    
]
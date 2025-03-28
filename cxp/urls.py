from django.urls import path
from . import views
from .views import(
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView, 
    ComprasView, compras,   
    CompraDetDelete, imprime_compra
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

   
    
]
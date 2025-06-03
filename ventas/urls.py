from django.urls import path
from . import views
from .views import(
    ProductoInmobiliario, CrearProductoInmobiliarioView, ProductoInmobiliarioListView, 
    ProductoInmobiliarioCreateView, ProductoInmobiliarioDeleteView, ProductoInmobiliarioUpdateView, vender_producto, 
    RegistrarVentaView, VentaCreateView, ClienteList, ClienteNew, ClienteEdit, ClienteDel, registrar_pago, 
    generar_recibo_pago, dashboard
) 



app_name = 'ven'

urlpatterns = [
    
    path('crear-producto-inmobiliario/', CrearProductoInmobiliarioView.as_view(), name='crear_producto_inmobiliario'),
    path('productoinmobiliario/', ProductoInmobiliarioListView.as_view(), name='productoinmobiliario_list'),
    path('productoinmobiliario/new/', ProductoInmobiliarioCreateView.as_view(), name='productoinmobiliario_new'),
    path('productoinmobiliario/edit/<int:pk>/', ProductoInmobiliarioUpdateView.as_view(), name='productoinmobiliario_edit'),
    path('productoinmobiliario/delete/<int:pk>/', ProductoInmobiliarioDeleteView.as_view(), name='productoinmobiliario_delete'),
    path('vender/<int:producto_id>/', views.vender_producto, name='vender_producto'),
    path('registrar-venta/', RegistrarVentaView.as_view(), name='registrar_venta'),
    path('productos/<int:producto_id>/asignar_cliente/', views.asignar_cliente, name='asignar_cliente'),
    path('dashboard/', dashboard, name='dashboard'),

    path('clientes/', ClienteList.as_view(), name='cliente_list'),
    path('clientes/nuevo/', ClienteNew.as_view(), name='cliente_new'),
    path('clientes/editar/<int:pk>/', ClienteEdit.as_view(), name='cliente_edit'),
    path('clientes/eliminar/<int:pk>/', ClienteDel.as_view(), name='cliente_del'),
    path('registrar_pago/<int:producto_id>/', registrar_pago, name='registrar_pago'),
    path('cliente/create/modal/', views.cliente_create_modal, name='cliente_create_modal'),
    path('buscar-clientes/', views.buscar_clientes, name='ruta_para_buscar_clientes'),
    path('recibo/<int:recibo_id>/', generar_recibo_pago, name='generar_recibo_pago'),
    
    

]

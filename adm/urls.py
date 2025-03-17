from django.urls import path
from . import views
from .views import(
    BancoView, BancoNew, BancoEdit, BancoDel,
    CuentaView, CuentaNew, CuentaEdit,
    ProyectoNew, ProyectoView, ProyectoEdit, ProyectoDel,
    ResidenteView, ResidenteNew, ResidenteEdit, ResidenteDel, proyecto_report,
    SimbologiaView, SimbologiaNew, SimbologiaEdit, SimbologiaDelete,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView, simbologia_pdf,
    ComprasView, compras, 
    EquipoListView, EquipoCreateView, EquipoUpdateView, EquipoDeleteView,
    RegistroCuentaListView, RegistroCuentaDel, RegistroCuentaEdit, RegistroCuentaReportView, RegistroCuentaCreateNew,
    registrocuenta_report, ReporteMovimientoView, generar_pdf, CompraDetDelete, BitacoraListView, BitacoraCreateView,
    BitacoraUpdateView, BitacoraDeleteView
) 



app_name = 'adm'

urlpatterns = [
    
    path('proveedor', ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedor/new/', ProveedorCreateView.as_view(), name='proveedor_new'),
    path('proveedor/edit/<int:pk>/', ProveedorUpdateView.as_view(), name='proveedor_edit'),
    path('proveedor/delete/<int:pk>/', ProveedorDeleteView.as_view(), name='proveedor_del'),
    

    path('bancos/', BancoView.as_view(), name="banco_list"),
    path('bancos/new/', BancoNew.as_view(), name="banco_new"),
    path('bancos/edit/<pk>/', BancoEdit.as_view(), name="banco_edit"),
    path('bancos/delete/<pk>/', BancoDel.as_view(), name="banco_del"),
    
    path('cuentas/', CuentaView.as_view(), name="cuenta_list"),
    path('cuentas/new/', CuentaNew.as_view(), name="cuenta_new"),
    path('cuentas/edit/<pk>/', CuentaEdit.as_view(), name="cuenta_edit"),
    path('reporte/<int:cuenta_id>/', ReporteMovimientoView.as_view(), name='reporte_movimiento'),
    path('reporte/registrocuenta/', registrocuenta_report, name='registrocuenta_report'),
    path('reporte/registrocuenta/report/pdf/', generar_pdf, name='registrocuenta_report_pdf'),
    path('registrocuenta/report/pdf/', generar_pdf, name='generar_pdf'),



    path('residentes/', ResidenteView.as_view(), name='residente_list'),
    path('residente/new/', ResidenteNew.as_view(), name='residente_new'),
    path('residente/edit/<int:pk>/', ResidenteEdit.as_view(), name='residente_edit'),
    path('residente/delete/<int:pk>/', ResidenteDel.as_view(), name='residente_del'),

    # URLs para Proyecto
    path('proyectos/', ProyectoView.as_view(), name='proyecto_list'),
    path('proyecto/new/', ProyectoNew.as_view(), name='proyecto_new'),
    path('proyecto/edit/<int:pk>/', ProyectoEdit.as_view(), name='proyecto_edit'),
    path('proyecto/delete/<int:pk>/', ProyectoDel.as_view(), name='proyecto_del'),
    path('proyecto/report/', proyecto_report, name='proyecto_report'),
    
    path('simbologias/', SimbologiaView.as_view(), name='simbologia_list'),
    path('simbologias/nuevo/', SimbologiaNew.as_view(), name='simbologia_new'),
    path('simbologias/editar/<int:pk>/', SimbologiaEdit.as_view(), name='simbologia_edit'),
    path('simbologias/eliminar/<int:pk>/', SimbologiaDelete.as_view(), name='simbologia_delete'),
    path('simbologias/pdf/', simbologia_pdf, name='simbologia_pdf'),
    
   
    
    path('compras',ComprasView.as_view(), name="compras_list"),
    path('compras/new',compras, name="compras_new"),
    path('compras/edit/<int:compra_id>',compras, name="compras_edit"),
    path('compras/<int:compra_id>/delete/<int:pk>', CompraDetDelete.as_view(), name="compras_del"),

   
    path('registrocuenta/', RegistroCuentaListView.as_view(), name='registrocuenta_list'),
    path('registrocuenta/nuevo/', RegistroCuentaCreateNew.as_view(), name='registrocuenta_new'),
    path('registrocuenta/editar/<int:pk>/', RegistroCuentaEdit.as_view(), name='registrocuenta_edit'),
    path('registrocuenta/eliminar/<int:pk>/', RegistroCuentaDel.as_view(), name='registrocuenta_del'),    
    path('registrocuenta/report/', registrocuenta_report, name='registrocuenta_report'),
    
    path('equipo/', EquipoListView.as_view(), name='equipo_list'),
    path('equipo/new/', EquipoCreateView.as_view(), name='equipo_new'),
    path('equipo/edit/<int:pk>/', EquipoUpdateView.as_view(), name='equipo_edit'),
    path('equipo/delete/<int:pk>/', EquipoDeleteView.as_view(), name='equipo_del'),

    path('bitacora/', BitacoraListView.as_view(), name='bitacora_list'),
    path('bitacora/new/', BitacoraCreateView.as_view(), name='bitacora_new'),
    path('bitacora/edit/', BitacoraUpdateView.as_view(), name='bitacora_edit'),

    
    

]

   


    

    





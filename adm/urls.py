from django.urls import path
from . import views
from .views import(
    BancoView, BancoNew, BancoEdit, BancoDel,
    CuentaView, CuentaNew, CuentaEdit,
    ProyectoNew, ProyectoView, ProyectoEdit, ProyectoDel,
    ResidenteView, ResidenteNew, ResidenteEdit, ResidenteDel, proyecto_report,
    SimbologiaView, SimbologiaNew, SimbologiaEdit, SimbologiaDelete,
    simbologia_pdf,
    EquipoListView, EquipoCreateView, EquipoUpdateView, EquipoDeleteView,
    registrocuenta_report, ReporteMovimientoView, generar_pdf, BitacoraListView, BitacoraCreateView,
    BitacoraUpdateView, BitacoraDeleteView, RegistroCuentaListView,RegistroCuentaCreateNew,RegistroCuentaEdit,RegistroCuentaDel,
    TipoPagoCreateView, TipoPagoListView, TipoPagoDeleteView, TipoPagoUpdateView, registrar_pago, listado_pagos, dashboard,
    compras_pagadas, reporte_egresos_pdf, generar_estado_cuenta_pdf, dashboard_proyectos, CargaCombustibleListView, CargaCombustibleCreateView,
    CargaCombustibleUpdateView, CargaCombustibleDeleteView, ReporteEquipoCreateView, ReporteEquipoListView, ReporteEquipoUpdateView,
    ReporteEquipoDeleteView, ReporteEquipoDetailView, PagoIndirectoListView, PagoIndirectoCreateView,
    PagoIndirectoDeleteView, PagoIndirectoUpdateView
) 



app_name = 'adm'

urlpatterns = [
    
    path('bancos/', BancoView.as_view(), name="banco_list"),
    path('bancos/new/', BancoNew.as_view(), name="banco_new"),
    path('bancos/edit/<pk>/', BancoEdit.as_view(), name="banco_edit"),
    path('bancos/delete/<pk>/', BancoDel.as_view(), name="banco_del"),
    path('compra/pago/<int:compra_id>/', registrar_pago, name='registrar_pago'),
    path('pagos/', listado_pagos, name='listado_pagos'),
    path('dashboard/', dashboard, name='dashboard'),
    path('compras-pagadas/', compras_pagadas, name='compras_pagadas'),
    path('reporte-egresos/', reporte_egresos_pdf, name='reporte_egresos'),
    path('estado_cuenta/<int:cuenta_id>/pdf/', generar_estado_cuenta_pdf, name='estado_cuenta_pdf'),
    
    path('cuentas/', CuentaView.as_view(), name="cuenta_list"),
    path('cuentas/new/', CuentaNew.as_view(), name="cuenta_new"),
    path('cuentas/edit/<pk>/', CuentaEdit.as_view(), name="cuenta_edit"),
    path('reporte/<int:cuenta_id>/', ReporteMovimientoView.as_view(), name='reporte_movimiento'),
    path('reporte/registrocuenta/', registrocuenta_report, name='registrocuenta_report'),
    path('reporte/registrocuenta/report/pdf/', generar_pdf, name='registrocuenta_report_pdf'),
    path('registrocuenta/report/pdf/', generar_pdf, name='generar_pdf'),

    path('registrocuenta/', RegistroCuentaListView.as_view(), name='registrocuenta_list'),
    path('registrocuenta/nuevo/', RegistroCuentaCreateNew.as_view(), name='registrocuenta_new'),
    path('registrocuenta/editar/<int:pk>/', RegistroCuentaEdit.as_view(), name='registrocuenta_edit'),
    path('registrocuenta/eliminar/<int:pk>/', RegistroCuentaDel.as_view(), name='registrocuenta_del'),    
    path('registrocuenta/report/', registrocuenta_report, name='registrocuenta_report'),
    
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
    path('dashboard-proyectos/', dashboard_proyectos, name='dashboard_proyectos'),
    
    path('simbologias/', SimbologiaView.as_view(), name='simbologia_list'),
    path('simbologias/nuevo/', SimbologiaNew.as_view(), name='simbologia_new'),
    path('simbologias/editar/<int:pk>/', SimbologiaEdit.as_view(), name='simbologia_edit'),
    path('simbologias/eliminar/<int:pk>/', SimbologiaDelete.as_view(), name='simbologia_delete'),
    path('simbologias/pdf/', simbologia_pdf, name='simbologia_pdf'),
    
    path('equipo/', EquipoListView.as_view(), name='equipo_list'),
    path('equipo/new/', EquipoCreateView.as_view(), name='equipo_new'),
    path('equipo/edit/<int:pk>/', EquipoUpdateView.as_view(), name='equipo_edit'),
    path('equipo/delete/<int:pk>/', EquipoDeleteView.as_view(), name='equipo_del'),

    
    path('bitacora/', BitacoraListView.as_view(), name='bitacora_list'),
    path('bitacora/new/', BitacoraCreateView.as_view(), name='bitacora_new'),
    path('bitacora/edit/<int:pk>/', BitacoraUpdateView.as_view(), name='bitacora_edit'),
    path('bitacora/delete/<int:pk>/', BitacoraDeleteView.as_view(), name='bitacora_delete'),


    path('tipopago/', TipoPagoListView.as_view(), name='tipopago_list'),
    path('tipopago/nuevo/', TipoPagoCreateView.as_view(), name='tipopago_new'),
    path('tipopago/editar/<int:pk>/', TipoPagoUpdateView.as_view(), name='tipopago_edit'),
    path('tipopago/eliminar/<int:pk>/', TipoPagoDeleteView.as_view(), name='tipopago_delete'),

    path('documentos/', views.documentos_list, name='documentos_list'),
    path('documentos/nuevo/', views.documento_create, name='documento_create'),
    path('documentos/eliminar/<int:pk>/', views.documento_delete, name='documento_delete'),

    path('combustible/', CargaCombustibleListView.as_view(), name='cargacombustible_list'),
    path('combustible/new/', CargaCombustibleCreateView.as_view(), name='cargacombustible_new'),
    path('combustible/edit/<int:pk>/', CargaCombustibleUpdateView.as_view(), name='cargacombustible_edit'),
    path('combustible/delete/<int:pk>/', CargaCombustibleDeleteView.as_view(), name='cargacombustible_delete'),
    path('reporte_combustible/', views.reporte_carga_combustible, name='reporte_combustible'),


    path('reportes/', views.ReporteEquipoListView.as_view(), name='reporte_equipo_list'),
    path('reportes/<int:pk>/', views.ReporteEquipoDetailView.as_view(), name='reporte_equipo_detail'),
    path('reportes/nuevo/', views.ReporteEquipoCreateView.as_view(), name='reporte_equipo_create'),
    path('reportes/<int:pk>/editar/', views.ReporteEquipoUpdateView.as_view(), name='reporte_equipo_update'),
    path('reportes/<int:pk>/eliminar/', views.ReporteEquipoDeleteView.as_view(), name='reporte_equipo_delete'),

    path("pagos-indirectos/", PagoIndirectoListView.as_view(), name="pagoindirecto_list"),
    path("pagos-indirectos/nuevo/", PagoIndirectoCreateView.as_view(), name="pagoindirecto_create"),
    path("pagos-indirectos/<int:pk>/editar/", PagoIndirectoUpdateView.as_view(), name="pagoindirecto_update"),
    path("pagos-indirectos/<int:pk>/eliminar/", PagoIndirectoDeleteView.as_view(), name="pagoindirecto_delete"),
    path('pagoindirecto/afectar/<int:pk>/', views.PagoIndirectoAfectarView.as_view(), name='pagoindirecto_afectar'),

    
]

   


    

    





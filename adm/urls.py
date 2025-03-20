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
    TipoPagoCreateView, TipoPagoListView, TipoPagoDeleteView, TipoPagoUpdateView, registrar_pago, listado_pagos
) 



app_name = 'adm'

urlpatterns = [
    
    path('bancos/', BancoView.as_view(), name="banco_list"),
    path('bancos/new/', BancoNew.as_view(), name="banco_new"),
    path('bancos/edit/<pk>/', BancoEdit.as_view(), name="banco_edit"),
    path('bancos/delete/<pk>/', BancoDel.as_view(), name="banco_del"),
    path('compra/pago/<int:compra_id>/', registrar_pago, name='registrar_pago'),
    path('pagos/', listado_pagos, name='listado_pagos'),
    
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
    path('bitacora/edit/', BitacoraUpdateView.as_view(), name='bitacora_edit'),

    path('tipopago/', TipoPagoListView.as_view(), name='tipopago_list'),
    path('tipopago/nuevo/', TipoPagoCreateView.as_view(), name='tipopago_new'),
    path('tipopago/editar/<int:pk>/', TipoPagoUpdateView.as_view(), name='tipopago_edit'),
    path('tipopago/eliminar/<int:pk>/', TipoPagoDeleteView.as_view(), name='tipopago_delete'),

    
]

   


    

    





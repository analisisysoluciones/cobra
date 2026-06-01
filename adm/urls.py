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
    PagoIndirectoDeleteView, PagoIndirectoUpdateView, reporte_equipo_view, OrdenServicioCreateView, OrdenServicioListView, 
    Equipo360View, reporte_pda, MantenimientoEquipoListView, MantenimientoEquipoCreateView, MantenimientoEquipoUpdateView, 
    MantenimientoEquipoDeleteView, crear_cuenta_ajax
    
) 

from adm.api import api_equipos_activos, captura_combustible
from adm.views_actividades import *
from .views_pda import *
from .views_dashboard import *
from .views_oficina import (oficina_actividades, editar_actividad, listado_actividades,captura_bloques_oficina, 
                            guardar_bloques_oficina, historial_bloques_ajax, actividades_por_equipo_ajax
                            )

from django.urls import path

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


    path("reporte-equipo/", reporte_equipo_view, name="reporte_equipo"),
    path('reporte-equipo/pdf/', views.reporte_equipo_pdf, name='reporte_equipo_pdf'),
    path('reporte-equipo/excel/', views.reporte_equipo_excel, name='reporte_equipo_excel'),

    
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
    path('cuentas/ajax/crear/',crear_cuenta_ajax,name='crear_cuenta_ajax'),
    
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

    path('orden-servicio/nueva/', OrdenServicioCreateView.as_view(), name='orden_servicio_create'),
    path('orden-servicio/', OrdenServicioListView.as_view(), name='orden_servicio_list'),

    path('api/equipos-activos/', api_equipos_activos, name='api_equipos_activos'),
    path('flotilla/captura/', captura_combustible, name='captura_combustible'),

    path('equipo/<int:pk>/360/', Equipo360View.as_view(), name='equipo_360'),
    path('pda/reporte/', reporte_pda, name='reporte_pda'),
    path('mantenimiento/', MantenimientoEquipoListView.as_view(), name='mantenimiento_list'),
    path('mantenimiento/new/', MantenimientoEquipoCreateView.as_view(), name='mantenimiento_new'),
    path('mantenimiento/edit/<int:pk>/', MantenimientoEquipoUpdateView.as_view(), name='mantenimiento_edit'),
    path('mantenimiento/delete/<int:pk>/', MantenimientoEquipoDeleteView.as_view(), name='mantenimiento_delete'),

    path('tipo-equipo/', TipoEquipoListView.as_view(), name='tipo_equipo_list'),
    path('tipo-equipo/nuevo/', TipoEquipoCreateView.as_view(), name='tipo_equipo_create'),
    path('tipo-equipo/editar/<int:pk>/', TipoEquipoUpdateView.as_view(), name='tipo_equipo_update'),
    path('tipo-equipo/eliminar/<int:pk>/', TipoEquipoDeleteView.as_view(), name='tipo_equipo_delete'),

    # Actividades
    path('actividades/', ActividadEquipoListView.as_view(), name='actividad_list'),
    path('actividades/nuevo/', ActividadEquipoCreateView.as_view(), name='actividad_create'),
    path('actividades/editar/<int:pk>/', ActividadEquipoUpdateView.as_view(), name='actividad_update'),
    path('actividades/eliminar/<int:pk>/', ActividadEquipoDeleteView.as_view(), name='actividad_delete'),

    path('pda/', pda_inicio, name='pda_inicio'),
    #path('pda/jornada/', pda_jornada, name='pda_jornada'),
    path('pda/iniciar/', iniciar_jornada, name='iniciar_jornada'),
    path('pda/actividad/', iniciar_actividad, name='iniciar_actividad'),
    path('pda/terminar/', terminar_jornada, name='terminar_jornada'),
    #path('pda/estado/', estado_pda, name='estado_pda'),
    path('pda/bloques/', captura_bloques, name='captura_bloques'),
    path('pda/bloques/guardar/', guardar_bloques, name='guardar_bloques'),
    path('pda/menu/', pda_menu, name='pda_menu'),
    path('operacion/actividades/', captura_bloques, name='actividades_escritorio'),

    # RENTAS

        
    
    
    path("pda/mis-movimientos/",mis_movimientos,name="mis_movimientos"),
    path("pda/escritorio/",jornada_escritorio,name="jornada_escritorio"),

    path("pda/escritorio/iniciar-actividad/",iniciar_actividad_escritorio, name="iniciar_actividad_escritorio"),

    path("pda/escritorio/cerrar/",terminar_jornada,name="cerrar_jornada_escritorio"),
    path("dashboard/maquinaria/",dashboard_maquinaria,name="dashboard_maquinaria"),
    path("pda/mobile/", pda_mobile_inicio, name="pda_mobile_inicio"),
    path("pda/mobile/operacion/", pda_mobile_operacion, name="pda_mobile_operacion"),
    

    path('oficina/actividades/', oficina_actividades, name='oficina_actividades'),
    path('oficina/actividad/<int:pk>/editar/', editar_actividad, name='editar_actividad'),

    path("proyectos/<int:pk>/360/", Proyecto360View.as_view(), name="proyecto_360"),

    path("proyectos/<int:pk>/360/finanzas/", proyecto360_finanzas_ajax, name="proyecto_360_finanzas"),
    #path("proyectos/<int:pk>/360/actividades/", proyecto360_actividades_ajax, name="proyecto_360_actividades"),
    path("proyectos/<int:pk>/360/compras/", proyecto360_compras_ajax, name="proyecto_360_compras"),
    path("proyectos/<int:pk>/360/nomina/", proyecto360_nomina_ajax, name="proyecto_360_nomina"),
    #path("proyectos/<int:pk>/360/clientes/", proyecto360_clientes_ajax, name="proyecto_360_clientes"),
    path("actividades/listado/",           listado_actividades,      name="listado_actividades"),
    path("actividades/captura-oficina/",   captura_bloques_oficina,  name="captura_bloques_oficina"),
    path("actividades/guardar-oficina/",   guardar_bloques_oficina,  name="guardar_bloques_oficina"),
    path("actividades/historial-ajax/",    historial_bloques_ajax,   name="historial_bloques_ajax"),    
    path("actividades/por-equipo/", actividades_por_equipo_ajax, name="actividades_por_equipo_ajax"),


    
    
]

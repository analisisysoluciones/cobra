# nomina/urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import ( 
    EmpleadoList, EmpleadoEdit, EmpleadoNew, EmpleadoDel,
    calcular_nomina_view,
    generar_nomina_pdf, procesar_nomina, generar_nomina_individual_pdf,
    PeriodosNominaList, PeriodosNominaNew, PeriodosNominaEdit, PeriodosNominaDel,
    DocumentoEmpleadoDelete, capturar_falta, validar_curp,
    AsistenciaListView, AsistenciaDeleteView, asignar_proyecto_individual,seleccionar_periodo_nomina,
    listar_detalles_nomina_procesada, procesar_nomina_form, NominaDetalleListView,
    NominaDetalleUpdateView, asignar_proyectos, cerrar_nomina, nominas_cerradas_list, asignar_semana_todos, 
    AsignacionCreateView, AsignacionListView, AsignacionUpdateView, AsignacionDeleteView, asignaciones_masivas,
    nomina_detalle, crear_asignacion_diaria
)

app_name = 'nom'

urlpatterns = [
    path('empleados/', EmpleadoList.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoNew.as_view(), name='empleado_create'),
    path('empleados/editar/<int:pk>/', EmpleadoEdit.as_view(), name='empleado_edit'),
    path('empleados/delete/<int:pk>/', EmpleadoDel.as_view(), name='empleado_del'),
    path('empleados/documento/eliminar/<int:pk>/', DocumentoEmpleadoDelete, name='documento_delete'), # Era DocumentoEmpleadoDelete.as_view(), pero es una función, no una clase
    path('falta/', capturar_falta, name='capturar_falta'),
    path('seleccionar-fecha/', seleccionar_periodo_nomina, name='seleccionar_fecha'),
    path('calcular-nomina/', calcular_nomina_view, name='calcular_nomina'), # Renombrado para evitar conflicto con calcular_nomina_semanal_todos si es que la tenías como vista
    path('asignar-semana/', asignar_semana_todos, name='asignar_semana'),
    path('asignaciones-list/', AsignacionListView.as_view(), name='asignacion_list'),
    path('asignaciones-nueva/', AsignacionCreateView.as_view(), name='asignacion_nueva'),
    path('asignaciones-edita/<int:pk>/', AsignacionUpdateView.as_view(), name='asignacion_edita'),
    path('asignaciones-elimina/<int:pk>/', AsistenciaDeleteView.as_view(), name='asignacion_elimina'),
    path('asignaciones-masivas/', asignaciones_masivas, name='asignaciones_masivas'),
    path('crear-asignacion/', crear_asignacion_diaria, name='crear_asignacion'),
    

    #path('nomina-semanal/pdf/', generar_nomina_pdf, name='nomina_pdf'),
    path('nomina-semanal/pdf/<str:fecha_str>/', generar_nomina_pdf, name='nomina_pdf'),

    #path('nomina-individual/pdf/', generar_nomina_individual_pdf, name='nomina_ind_pdf'),
    path('nomina-individual/pdf/<str:fecha_str>/', generar_nomina_individual_pdf, name='nomina_ind_pdf'),

    path('procesar-nomina/', procesar_nomina, name='procesar_nomina'),
    
    path('cerrar-nomina/<int:pk>/',cerrar_nomina,name='cerrar_nomina'),
    path('nominas-cerradas/', nominas_cerradas_list, name='nominas_cerradas_list'),
    path('nomina-detalle/<int:pk>/', nomina_detalle, name='nomina_detalle'),


    path('periodos/', PeriodosNominaList.as_view(), name='periodos_list'),
    path('periodos/nuevo/', PeriodosNominaNew.as_view(), name='periodos_new'),
    path('periodos/editar/<int:pk>/', PeriodosNominaEdit.as_view(), name='periodos_edit'),
    path('periodos/eliminar/<int:pk>/', PeriodosNominaDel.as_view(), name='periodos_del'),
    path('formulario-procesar/', procesar_nomina_form, name='procesar_nomina_form'),

    path('validar-curp/', validar_curp, name='validar_curp'),
    path("asistencias/", AsistenciaListView.as_view(), name="asistencia_list"),
    path("asistencias/delete/<int:pk>/", AsistenciaDeleteView.as_view(), name="asistencia_delete"), # Agregado barra final para consistencia

    # URLs para el flujo de nómina procesada y asignación de proyectos
    path('nomina/detalles-procesados/<int:nomina_historial_id>/', listar_detalles_nomina_procesada, name='listar_detalles_nomina_procesada'),
    path('nomina/detalle/<int:detalle_id>/asignar-proyecto/', asignar_proyecto_individual, name='asignar_proyecto_individual'),
    path('asignar-proyectos/<int:nomina_id>/', asignar_proyectos, name='asignar_proyectos'),
    #path('nomina/<int:pk>/', NominaDetalleView.as_view(), name='tu_url_de_detalle_nomina'), # Asegúrate de tener una URL para el detalle
    #path('nomina/exito/', NominaExitoView.as_view(), name='tu_url_de_exito_nomina'), # Una URL para el éxito

    path('editar-proyecto/<int:pk>/', NominaDetalleUpdateView.as_view(), name='editar_proyecto'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
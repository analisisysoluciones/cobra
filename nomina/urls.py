# nomina/urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from nomina.views.cerrar_nomina import cerrar_nomina, nominas_cerradas_list

# --- IMPORTS DE VISTAS ---
from nomina.views.empleados import (
    EmpleadoList, EmpleadoEdit, EmpleadoNew, EmpleadoDel,
    DocumentoEmpleadoDelete, validar_curp
)

from nomina.views.asistencia import (
    AsistenciaListView, AsistenciaDeleteView, capturar_falta, CapturarFaltaModalView
)

from nomina.views.periodos import (
    PeriodosNominaList, PeriodosNominaNew, PeriodosNominaEdit, PeriodosNominaDel,
    seleccionar_periodo_nomina, procesar_nomina_form
)

from nomina.views.horas_extras import horas_extras_list, horas_extras_new, HorasExtrasEmpleadoCreateView

from nomina.views.nomina_calculo import calcular_nomina_view, reiniciar_nomina

from nomina.views.pdf import (
    generar_nomina_pdf, generar_nomina_individual_pdf, exportar_periodos_pdf, generar_nomina_asignaciones_pdf,
    generar_auditoria_nomina_pdf
)


from nomina.views.compensaciones import (CompensacionVariableListView, CompensacionVariableCreateView, CompensacionVariableDeleteView,
                                       CompensacionVariableUpdateView
                                       )
# HORAS EXTRAS


from nomina.views.nomina_detalle import (
    listar_detalles_nomina_procesada,
     nomina_detalle
)

from nomina.views.asignaciones import (
    asignar_semana_todos, AsignacionCreateView, AsignacionListView,
    AsignacionUpdateView, AsignacionDeleteView, asignaciones_masivas,
    crear_asignacion_diaria
)

from nomina.views.destajos import (
    TarifaDestajoObraCreateView, TarifaDestajoObraDeleteView, TarifaDestajoObraListView,
    TarifaDestajoObraUpdateView, TipoDestajoCreateView, TipoDestajoDeleteView,
    TipoDestajoListView, TipoDestajoUpdateView
)

from nomina.views.nomina_procesar import (procesar_nomina, procesar_nomina_form)

from nomina.views.proyectos import (asignar_proyecto_individual, NominaDetalleUpdateView, NominaDetalleListView, asignar_proyectos)

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
    path("asistencia/falta/<int:empleado_id>/", CapturarFaltaModalView.as_view(), name="capturar_falta_modal"),

    
    path('asignar-semana/', asignar_semana_todos, name='asignar_semana'),
    path('asignaciones-list/', AsignacionListView.as_view(), name='asignacion_list'),
    path('asignaciones-nueva/', AsignacionCreateView.as_view(), name='asignacion_nueva'),
    path('asignaciones-edita/<int:pk>/', AsignacionUpdateView.as_view(), name='asignacion_edita'),
    path('asignaciones-elimina/<int:pk>/', AsignacionDeleteView.as_view(), name='asignacion_elimina'),
    path('asignaciones-masivas/', asignaciones_masivas, name='asignaciones_masivas'),
    path('nomina/asignaciones/pdf/<str:fecha_inicio_str>/<str:fecha_fin_str>/', generar_nomina_asignaciones_pdf, name='generar_nomina_asignaciones_pdf'),

    
    path('crear-asignacion/', crear_asignacion_diaria, name='crear_asignacion'),
    path("destajos/", TipoDestajoListView.as_view(), name="tipo_destajo_list"),
    path("destajos/nuevo/", TipoDestajoCreateView.as_view(), name="tipo_destajo_create"),
    path("destajos/editar/<int:pk>/", TipoDestajoUpdateView.as_view(), name="tipo_destajo_update"),
    path("destajos/eliminar/<int:pk>/", TipoDestajoDeleteView.as_view(), name="tipo_destajo_delete"),
    path('reiniciar/', reiniciar_nomina, name='reiniciar_nomina'),

    # Tarifas por obra
    path("tarifas_destajo/", TarifaDestajoObraListView.as_view(), name="tarifa_destajo_obra_list"),
    path("tarifas_destajo/nuevo/", TarifaDestajoObraCreateView.as_view(), name="tarifa_destajo_obra_create"),
    path("tarifas_destajo/editar/<int:pk>/", TarifaDestajoObraUpdateView.as_view(), name="tarifa_destajo_obra_update"),
    path("tarifas_destajo/eliminar/<int:pk>/", TarifaDestajoObraDeleteView.as_view(), name="tarifa_destajo_obra_delete"),
    

    #path('nomina-semanal/pdf/', generar_nomina_pdf, name='nomina_pdf'),
    path('nomina-semanal/pdf/<str:fecha_str>/', generar_nomina_pdf, name='nomina_pdf'),
    #path("auditoria/<int:periodo_id>/", generar_auditoria_nomina_pdf, name="auditoria_nomina_pdf"),
    path("auditoria/<int:historial_id>/", generar_auditoria_nomina_pdf, name="auditoria_nomina_pdf"),



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

    path('horas-extras/', horas_extras_list, name='horas_extras_list'),
    path('horas-extras/nuevo/', horas_extras_new, name='horas_extras_new'),
    path('periodos/pdf/', exportar_periodos_pdf, name='periodos_pdf'),


    # URLs para el flujo de nómina procesada y asignación de proyectos
    path('nomina/detalles-procesados/<int:nomina_historial_id>/', listar_detalles_nomina_procesada, name='listar_detalles_nomina_procesada'),
    path('nomina/detalle/<int:detalle_id>/asignar-proyecto/', asignar_proyecto_individual, name='asignar_proyecto_individual'),
    path('asignar-proyectos/<int:nomina_id>/', asignar_proyectos, name='asignar_proyectos'),
    #path('nomina/<int:pk>/', NominaDetalleView.as_view(), name='tu_url_de_detalle_nomina'), # Asegúrate de tener una URL para el detalle
    #path('nomina/exito/', NominaExitoView.as_view(), name='tu_url_de_exito_nomina'), # Una URL para el éxito
    path('horas-extras/nuevo/<int:empleado_id>/', HorasExtrasEmpleadoCreateView.as_view(), name='horas_extras_create_emp'),
    path('compensacion-variable/nuevo/<int:empleado_id>/', CompensacionVariableCreateView.as_view(), name='compensacion_variable_create_emp'),


    path('editar-proyecto/<int:pk>/', NominaDetalleUpdateView.as_view(), name='editar_proyecto'),
    path("compensaciones/", CompensacionVariableListView.as_view(), name="compensacion_variable_list"),
    path("compensaciones/nuevo/", CompensacionVariableCreateView.as_view(), name="compensacion_variable_create"),
    path("compensaciones/editar/<int:pk>/", CompensacionVariableUpdateView.as_view(), name="compensacion_variable_update"),
    path("compensaciones/eliminar/<int:pk>/", CompensacionVariableDeleteView.as_view(), name="compensacion_variable_delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
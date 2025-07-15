# nomina/urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import ( # Importa todas las vistas que usas directamente
    EmpleadoList, EmpleadoEdit, EmpleadoNew, EmpleadoDel,
    seleccionar_fecha, calcular_nomina_view,
    generar_nomina_pdf, procesar_nomina, generar_nomina_individual_pdf,
    PeriodosNominaList, PeriodosNominaNew, PeriodosNominaEdit, PeriodosNominaDel,
    DocumentoEmpleadoDelete, capturar_falta, validar_curp,
    AsistenciaListView, AsistenciaDeleteView, asignar_proyecto_individual,
    listar_detalles_nomina_procesada # <-- Vista clave para detalles de nómina
)

app_name = 'nom'

urlpatterns = [
    path('empleados/', EmpleadoList.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoNew.as_view(), name='empleado_create'),
    path('empleados/editar/<int:pk>/', EmpleadoEdit.as_view(), name='empleado_edit'),
    path('empleados/delete/<int:pk>/', EmpleadoDel.as_view(), name='empleado_del'),
    path('empleados/documento/eliminar/<int:pk>/', DocumentoEmpleadoDelete, name='documento_delete'), # Era DocumentoEmpleadoDelete.as_view(), pero es una función, no una clase
    path('falta/', capturar_falta, name='capturar_falta'),
    path('seleccionar-fecha/', seleccionar_fecha, name='seleccionar_fecha'),
    path('calcular-nomina/', calcular_nomina_view, name='calcular_nomina'), # Renombrado para evitar conflicto con calcular_nomina_semanal_todos si es que la tenías como vista
    path('nomina-semanal/pdf/', generar_nomina_pdf, name='nomina_pdf'),
    path('procesar-nomina/', procesar_nomina, name='procesar_nomina'),
    path('nomina-individual/pdf/', generar_nomina_individual_pdf, name='nomina_ind_pdf'),

    path('periodos/', PeriodosNominaList.as_view(), name='periodos_list'),
    path('periodos/nuevo/', PeriodosNominaNew.as_view(), name='periodos_new'),
    path('periodos/editar/<int:pk>/', PeriodosNominaEdit.as_view(), name='periodos_edit'),
    path('periodos/eliminar/<int:pk>/', PeriodosNominaDel.as_view(), name='periodos_del'),

    path('validar-curp/', validar_curp, name='validar_curp'),
    path("asistencias/", AsistenciaListView.as_view(), name="asistencia_list"),
    path("asistencias/delete/<int:pk>/", AsistenciaDeleteView.as_view(), name="asistencia_delete"), # Agregado barra final para consistencia

    # URLs para el flujo de nómina procesada y asignación de proyectos
    path('nomina/detalles-procesados/<int:nomina_historial_id>/', listar_detalles_nomina_procesada, name='listar_detalles_nomina_procesada'),
    path('nomina/detalle/<int:detalle_id>/asignar-proyecto/', asignar_proyecto_individual, name='asignar_proyecto_individual'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
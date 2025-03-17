from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import(
    EmpleadoList, EmpleadoEdit, EmpleadoNew, EmpleadoDel, calcular_nomina_semanal_todos, seleccionar_fecha, calcular_nomina_view,
    generar_nomina_pdf,  procesar_nomina, generar_nomina_individual_pdf, PeriodosNominaList, PeriodosNominaNew, 
    PeriodosNominaEdit, PeriodosNominaDel, DocumentoEmpleadoDelete, capturar_falta, validar_curp,
    AsistenciaListView, AsistenciaDeleteView
) 



app_name = 'nom'

urlpatterns = [
    path('empleados/', EmpleadoList.as_view(), name='empleado_list'),
    path('empleados/crear/', EmpleadoNew.as_view(), name='empleado_create'),
    path('empleados/editar/<int:pk>/', EmpleadoEdit.as_view(), name='empleado_edit'),
    path('empleados/delete/<int:pk>/', EmpleadoDel.as_view(), name='empleado_del'),
    path('empleados/documento/eliminar/<int:pk>/', DocumentoEmpleadoDelete.as_view(), name='documento_delete'),

    path('falta/', views.capturar_falta, name='capturar_falta'),
    path('seleccionar-fecha/', seleccionar_fecha, name='seleccionar_fecha'),
    path('calcular-nomina/', calcular_nomina_view, name='calcular_nomina'),
    path('nomina-semanal/pdf/', generar_nomina_pdf, name='nomina_pdf'),
    path('procesar-nomina/', procesar_nomina, name='procesar_nomina'),
    path('nomina-individual/pdf/', generar_nomina_individual_pdf, name='nomina_ind_pdf'),

    path('periodos/', PeriodosNominaList.as_view(), name='periodos_list'),
    path('periodos/nuevo/', PeriodosNominaNew.as_view(), name='periodos_new'),
    path('periodos/editar/<int:pk>/', PeriodosNominaEdit.as_view(), name='periodos_edit'),
    path('periodos/eliminar/<int:pk>/', PeriodosNominaDel.as_view(), name='periodos_del'),
    
    path('validar-curp/', validar_curp, name='validar_curp'),
    path("asistencias/", AsistenciaListView.as_view(), name="asistencia_list"),
    path("asistencias/delete/<int:pk>", AsistenciaDeleteView.as_view(), name="asistencia_delete"),

     
] 

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
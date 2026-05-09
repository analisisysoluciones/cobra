from django.urls import path
from .views import ( CategoriaView, CategoriaNew, CategoriaEdit, CategoriaDel, MaterialNew, MaterialView, 
                    UnidadNew, UnidadView, UnidadEdit, UnidadDel, MaterialEdit, MaterialDel, generar_reporte_materiales,
                    RequisicionListView, RequisicionPDFView, Requisicion, requisicion_list, requisicion_pdf, ItemRequisicionDelete,
                    requisiciones, requisiciones_add_detalle_view, requisicion_entregar, reporte_requisiciones,
                    reporte_requisiciones_pdf,
                    SalidaAlmacenCreateView, SalidaAlmacenDetalleView, SalidaAlmacenListView
                    )



app_name = 'inv'  # Asegúrate de que el nombre de la aplicación sea correcto

urlpatterns = [
    path('categorias/',CategoriaView.as_view(), name="categoria_list"),
    path('categorias/new',CategoriaNew.as_view(), name="categoria_new"),
    path('categorias/edit/<int:pk>',CategoriaEdit.as_view(), name="categoria_edit"),
    path('categorias/delete/<int:pk>',CategoriaDel.as_view(), name="categoria_del"),

    # URLs para Unidad
    path('unidad/', UnidadView.as_view(), name='unidad_list'),
    path('unidad/new/', UnidadNew.as_view(), name='unidad_new'),
    path('unidad/edit/<int:pk>/', UnidadEdit.as_view(), name='unidad_edit'),
    path('unidad/delete/<int:pk>/', UnidadDel.as_view(), name='unidad_del'),

    # URLs para Material
    path('material/', MaterialView.as_view(), name='material_list'),
    path('material/new/', MaterialNew.as_view(), name='material_new'),
    path('material/edit/<int:pk>/', MaterialEdit.as_view(), name='material_edit'),
    path('material/delete/<int:pk>/', MaterialDel.as_view(), name='material_del'),
    path('inv/material/reporte/', generar_reporte_materiales, name='material_rpt'),

    path('requisiciones/', requisicion_list, name='requisicion_list'),
    path('requisiciones/crear/', requisiciones, name='requisicion_create'),
    path('requisiciones/editar/<int:requisicion_id>/', requisiciones, name='requisicion_edit'),
    path('requisiciones/pdf/<int:pk>/', RequisicionPDFView.as_view(), name='requisicion_pdf'),
    path('item/delete/<int:pk>/', ItemRequisicionDelete.as_view(), name='item_requisiciones_del'),
    path('requisiciones/<int:requisicion_id>/add-detalle/', requisiciones_add_detalle_view, name='requisiciones_add_detalle'),
    path('requisiciones/<int:requisicion_id>/entregar/', requisicion_entregar, name='requisicion_entregar'),
    path('reporte/requisiciones/', reporte_requisiciones, name='reporte_requisiciones'),
    path('reporte/requisiciones/pdf/', reporte_requisiciones_pdf, name='reporte_requisiciones_pdf'),

    path('salida-almacen/nueva/', SalidaAlmacenCreateView.as_view(), name='salida_almacen_create'),
    path('salida-almacen/<int:pk>/', SalidaAlmacenDetalleView.as_view(), name='salida_almacen_detalle'),
    path('salida-almacen/', SalidaAlmacenListView.as_view(), name='salida_almacen_list'),





]







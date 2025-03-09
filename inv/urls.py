from django.urls import path
from .views import CategoriaView, CategoriaNew, CategoriaEdit, CategoriaDel, MaterialNew, MaterialView, UnidadNew, UnidadView, UnidadEdit, UnidadDel, MaterialEdit, MaterialDel, generar_reporte_materiales


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


]







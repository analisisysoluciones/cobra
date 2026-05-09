from django.contrib import admin

# Register your models here.
from .models import MantenimientoEquipo

@admin.register(MantenimientoEquipo)
class MantenimientoEquipoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'proyecto', 'tipo', 'fecha', 'costo')
    list_filter = ('tipo', 'fecha')
    search_fields = ('equipo__descripcion', 'descripcion', 'proveedor')
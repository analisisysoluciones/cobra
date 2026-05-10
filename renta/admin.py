from django.contrib import admin

from .models import ConceptoRentaCatalogo


@admin.register(ConceptoRentaCatalogo)
class ConceptoRentaCatalogoAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "precio_default",
        "activo"
    )

    search_fields = (
        "nombre",
    )

    list_filter = (
        "activo",
    )
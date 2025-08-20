# templatetags/custom_filters.py

from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica el valor por un argumento"""
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0
    
@register.filter
def add(value, arg):
    return value + arg  # Asegúrate de que la función hace lo correcto

@register.filter
def add_days(value, days):
    return value + timedelta(days=days)


@register.filter
def get_item(dictionary, key):
    return dictionary.get((key, None))

@register.filter
def fecha_match(asignaciones_dict, fecha):
    # asignaciones_dict es un dict con clave (empleado_id, fecha)
    # pero get_item no funcionaría directo porque necesitamos 2 llaves
    return asignaciones_dict.get(fecha, None)

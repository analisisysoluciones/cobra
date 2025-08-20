# nomina/templatetags/nom_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un item del diccionario usando una clave dinámica"""
    return dictionary.get(key)

@register.simple_tag
def get_asignacion(asignaciones_dict, emp_id, fecha):
    """Obtiene la asignación para un empleado en una fecha específica"""
    clave = f"{emp_id}_{fecha}"
    return asignaciones_dict.get(clave, '')
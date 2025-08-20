from django import template

register = template.Library()

@register.filter
def get_asignacion(dictionary, empleado_id):
    """Devuelve un subdiccionario de asignaciones para un empleado_id."""
    return {k[1]: v for k, v in dictionary.items() if k[0] == empleado_id}

@register.filter
def lookup(dictionary, key):
    """Devuelve el valor de una clave en un diccionario, o None si no existe."""
    return dictionary.get(key)
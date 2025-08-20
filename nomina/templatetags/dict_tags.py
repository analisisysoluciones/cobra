# nomina/templatetags/dict_tags.py
from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    if isinstance(key, str) and ',' in key:
        emp_id, fecha = key.split(',')
        fecha = fecha.strip()  # Limpiar espacios
        try:
            from datetime import datetime
            fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
            return dictionary.get((int(emp_id), fecha))
        except ValueError:
            return None
    return dictionary.get(key)
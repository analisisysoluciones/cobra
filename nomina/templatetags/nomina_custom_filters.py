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

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css):
    """Permite agregar clases CSS a campos de formulario desde el template."""
    return field.as_widget(attrs={"class": css})

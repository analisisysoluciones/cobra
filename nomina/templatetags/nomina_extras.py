from django import template

register = template.Library()

@register.filter
def total_field(items, field):
    total = 0
    if not items:
        return 0

    for row in items:
        # row es un dict: row["percepciones"]
        try:
            total += row.get(field, 0) or 0
        except:
            pass

    return total

from django import template

register = template.Library()

@register.filter
def abs_value(value):
    """Returns the absolute value of the number."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def split(value, delimiter=','):
    """Splits the string by the given delimiter."""
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter)]

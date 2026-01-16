from django import template
import re

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """
    Split a string using the specified delimiter, supporting whitespace trimming
    """
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter)]

@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument
    """
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0 
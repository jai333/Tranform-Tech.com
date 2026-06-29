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

@register.filter
def replace(value, arg):
    """
    Replace occurrences of string in value.
    Syntax: value|replace:"target,replacement" or value|replace:"target" (replaces with empty string)
    """
    if not isinstance(value, str):
        return value
    if ',' in arg:
        target, replacement = arg.split(',', 1)
    else:
        target, replacement = arg, ''
    return value.replace(target, replacement) 
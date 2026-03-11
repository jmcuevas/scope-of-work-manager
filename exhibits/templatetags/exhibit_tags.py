from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Allow dict access with a variable key: {{ mydict|get_item:variable }}"""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)

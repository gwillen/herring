import json

from django import template

from puzzles.models import to_json_value

register = template.Library()

@register.filter(name='to_json')
def to_json(data):
    return json.dumps(to_json_value(data))

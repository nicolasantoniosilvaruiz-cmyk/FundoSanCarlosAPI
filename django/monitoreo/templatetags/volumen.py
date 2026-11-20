from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def volumen_en(litros, estanque):
    cantidad = estanque.volumen_visible(litros)
    return f'{floatformat(cantidad, "0g")} {estanque.unidad_volumen}'

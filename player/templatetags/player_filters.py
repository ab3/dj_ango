import datetime
from django import template

register = template.Library()

@register.filter
def sec_to_hms(value):
    """Convert the number of seconds in value to h:m:s of m:s"""
    m, s = divmod(value, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, s) if h > 0 else '%02d:%02d' % (m, s)
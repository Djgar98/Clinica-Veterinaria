from django import template

register = template.Library()


@register.filter(name="fix_mojibake")
def fix_mojibake(value):
    """Attempt to repair common UTF-8 text that was decoded as latin-1/cp1252."""
    if not isinstance(value, str) or not value:
        return value

    markers = ("Ã", "â", "Â", "ï»¿")
    if not any(m in value for m in markers):
        return value

    try:
        return value.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value

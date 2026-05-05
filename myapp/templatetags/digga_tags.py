from django import template

register = template.Library()

@register.filter
def split(value, sep=","):
    return [item.strip() for item in str(value).split(sep) if item.strip()]

@register.filter
def currency(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"

@register.filter
def status_class(value):
    mapping = {
        "pending": "yellow",
        "accepted": "blue",
        "ongoing": "purple",
        "completed": "green",
        "cancelled": "red",
        "available": "green",
        "busy": "orange",
        "inactive": "gray",
    }
    return mapping.get(str(value).lower(), "gray")
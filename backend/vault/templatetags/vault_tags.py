from django import template

register = template.Library()

CATEGORY_ICONS = {
    "login": "key",
    "card": "card",
    "note": "note",
    "api_key": "code",
    "wifi": "wifi",
    "identity": "id",
}

ACTION_ICONS = {
    "login": "logout",
    "login_failed": "alert",
    "logout": "lock",
    "create": "plus",
    "update": "edit",
    "delete": "trash",
    "reveal": "eye",
    "copy": "copy",
    "export": "download",
    "password_change": "key",
}

STRENGTH_TONES = ["danger", "danger", "warning", "success", "success"]
STRENGTH_LABELS = ["Very weak", "Weak", "Fair", "Strong", "Excellent"]


@register.filter
def category_icon(category):
    return CATEGORY_ICONS.get(category, "key")


@register.filter
def action_icon(action):
    return ACTION_ICONS.get(action, "activity")


@register.filter
def strength_tone(score):
    if score is None:
        return ""
    return STRENGTH_TONES[int(score)]


@register.filter
def strength_label(score):
    if score is None:
        return ""
    return STRENGTH_LABELS[int(score)]


@register.simple_tag(takes_context=True)
def query_toggle(context, key, value):
    """Return the current querystring with ``key`` set to ``value`` (or removed if equal)."""
    params = context["request"].GET.copy()
    if params.get(key) == str(value):
        params.pop(key)
    else:
        params[key] = value
    params.pop("page", None)
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"

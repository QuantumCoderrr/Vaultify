from django.conf import settings


def vault_globals(request):
    return {
        "VAULT_SESSION_TIMEOUT": settings.SESSION_COOKIE_AGE,
    }

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import ActivityLog


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    if request is not None:
        ActivityLog.record(request, ActivityLog.Action.LOGIN, user=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if request is not None and user is not None:
        ActivityLog.record(request, ActivityLog.Action.LOGOUT, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    if request is None:
        return
    username = credentials.get("username")
    user = get_user_model().objects.filter(username=username).first() if username else None
    if user is not None:
        ActivityLog.record(request, ActivityLog.Action.LOGIN_FAILED, user=user)

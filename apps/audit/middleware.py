from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import log_action, AuditLog


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_action(user, AuditLog.ACTION_LOGIN, description=f'Вход в систему', request=request)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user:
        log_action(user, AuditLog.ACTION_LOGOUT, description='Выход из системы', request=request)


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

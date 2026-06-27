import logging
from django.db import models

logger = logging.getLogger('apps.audit')


class AuditLog(models.Model):
    ACTION_LOGIN  = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CANCEL = 'cancel'
    ACTION_VIEW   = 'view'
    ACTION_EXPORT = 'export'

    ACTION_CHOICES = [
        (ACTION_LOGIN,  'Вход'),
        (ACTION_LOGOUT, 'Выход'),
        (ACTION_CREATE, 'Создание'),
        (ACTION_UPDATE, 'Изменение'),
        (ACTION_DELETE, 'Удаление'),
        (ACTION_CANCEL, 'Отмена'),
        (ACTION_VIEW,   'Просмотр'),
        (ACTION_EXPORT, 'Экспорт'),
    ]

    ACTION_COLORS = {
        ACTION_LOGIN:  'success',
        ACTION_LOGOUT: 'secondary',
        ACTION_CREATE: 'primary',
        ACTION_UPDATE: 'warning',
        ACTION_DELETE: 'danger',
        ACTION_CANCEL: 'danger',
        ACTION_VIEW:   'info',
        ACTION_EXPORT: 'info',
    }

    user = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='audit_logs', verbose_name='Пользователь'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    model_name = models.CharField(max_length=100, blank=True, db_index=True, verbose_name='Модель')
    object_id = models.IntegerField(null=True, blank=True, db_index=True, verbose_name='ID объекта')
    object_repr = models.CharField(max_length=300, blank=True, verbose_name='Объект')
    description = models.TextField(blank=True, verbose_name='Описание')

    # Before / after values for financial changes
    old_value = models.TextField(blank=True, verbose_name='Старое значение')
    new_value = models.TextField(blank=True, verbose_name='Новое значение')

    # IP stored for security audit; shown only to directors/admins in templates
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Время')

    class Meta:
        verbose_name = 'Журнал действий'
        verbose_name_plural = 'Журнал действий'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        return f'{self.user} — {self.get_action_display()} — {self.timestamp}'

    @property
    def action_color(self):
        return self.ACTION_COLORS.get(self.action, 'secondary')


def _safe_ip(request) -> str | None:
    """Extract the real client IP from a request, safe against header spoofing."""
    if request is None:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        ip = x_forwarded.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip[:45] if ip else None   # GenericIPAddressField max length


def log_action(
    user,
    action: str,
    model_name: str = '',
    object_id: int | None = None,
    object_repr: str = '',
    description: str = '',
    old_value: str = '',
    new_value: str = '',
    request=None,
) -> AuditLog | None:
    """
    Create an AuditLog entry. Never raises — a logging failure must not break
    business logic. Errors are written to the 'apps.audit' logger instead.
    """
    try:
        entry = AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name[:100],
            object_id=object_id,
            object_repr=str(object_repr)[:300],
            description=description[:2000] if description else '',
            old_value=old_value[:2000] if old_value else '',
            new_value=new_value[:2000] if new_value else '',
            ip_address=_safe_ip(request),
        )
        return entry
    except Exception as exc:                # pragma: no cover
        logger.error('Failed to write audit log: %s', exc, exc_info=True)
        return None

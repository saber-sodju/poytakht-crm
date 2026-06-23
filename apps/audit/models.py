from django.db import models


class AuditLog(models.Model):
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_VIEW = 'view'

    ACTION_CHOICES = [
        (ACTION_LOGIN, 'Вход'),
        (ACTION_LOGOUT, 'Выход'),
        (ACTION_CREATE, 'Создание'),
        (ACTION_UPDATE, 'Изменение'),
        (ACTION_DELETE, 'Удаление'),
        (ACTION_VIEW, 'Просмотр'),
    ]

    ACTION_COLORS = {
        ACTION_LOGIN: 'success',
        ACTION_LOGOUT: 'secondary',
        ACTION_CREATE: 'primary',
        ACTION_UPDATE: 'warning',
        ACTION_DELETE: 'danger',
        ACTION_VIEW: 'info',
    }

    user = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='audit_logs', verbose_name='Пользователь'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Действие')
    model_name = models.CharField(max_length=100, blank=True, verbose_name='Модель')
    object_id = models.IntegerField(null=True, blank=True, verbose_name='ID объекта')
    object_repr = models.CharField(max_length=300, blank=True, verbose_name='Объект')
    description = models.TextField(blank=True, verbose_name='Описание')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')

    class Meta:
        verbose_name = 'Журнал действий'
        verbose_name_plural = 'Журнал действий'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.user} — {self.get_action_display()} — {self.timestamp}'

    @property
    def action_color(self):
        return self.ACTION_COLORS.get(self.action, 'secondary')


def log_action(user, action, model_name='', object_id=None, object_repr='', description='', request=None):
    ip = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=str(object_repr)[:300],
        description=description[:500] if description else '',
        ip_address=ip,
    )

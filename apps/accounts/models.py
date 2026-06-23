from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_DIRECTOR = 'director'
    ROLE_ADMIN = 'admin'
    ROLE_MANAGER = 'manager'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_CLIENT = 'client'

    ROLE_CHOICES = [
        (ROLE_DIRECTOR, 'Директор'),
        (ROLE_ADMIN, 'Главный администратор'),
        (ROLE_MANAGER, 'Менеджер / Ресепшн'),
        (ROLE_ACCOUNTANT, 'Бухгалтер'),
        (ROLE_CLIENT, 'Клиент'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MANAGER, verbose_name='Роль')
    phone = models.CharField(max_length=25, blank=True, verbose_name='Телефон')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_director(self):
        return self.role == self.ROLE_DIRECTOR

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER

    @property
    def is_accountant(self):
        return self.role == self.ROLE_ACCOUNTANT

    @property
    def is_client_role(self):
        return self.role == self.ROLE_CLIENT

    @property
    def can_manage_complex(self):
        return self.role in (self.ROLE_DIRECTOR, self.ROLE_ADMIN)

    @property
    def can_see_finance(self):
        return self.role in (self.ROLE_DIRECTOR, self.ROLE_ADMIN, self.ROLE_ACCOUNTANT)

    @property
    def can_manage_users(self):
        return self.role == self.ROLE_DIRECTOR

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class Notification(models.Model):
    TYPE_CHOICES = [
        ('payment_overdue', 'Просроченный платёж'),
        ('payment_today', 'Платёж сегодня'),
        ('booking_expiring', 'Бронь заканчивается'),
        ('budget_exceeded', 'Бюджет превышен'),
        ('new_sale', 'Новая продажа'),
        ('new_expense', 'Новый расход'),
        ('info', 'Информация'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f'{self.title} → {self.user}'

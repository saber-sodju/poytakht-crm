from django.db import models
from django.conf import settings


class Client(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='client_profile',
        verbose_name='Аккаунт клиента'
    )
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    phone = models.CharField(max_length=25, verbose_name='Телефон')
    phone2 = models.CharField(max_length=25, blank=True, verbose_name='Доп. телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    passport_series = models.CharField(max_length=20, blank=True, verbose_name='Серия паспорта')
    passport_number = models.CharField(max_length=20, blank=True, verbose_name='Номер паспорта')
    passport_issued_by = models.CharField(max_length=300, blank=True, verbose_name='Кем выдан')
    passport_date = models.DateField(null=True, blank=True, verbose_name='Дата выдачи')
    address = models.TextField(blank=True, verbose_name='Адрес')
    note = models.TextField(blank=True, verbose_name='Примечание')
    added_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='added_clients', verbose_name='Добавил'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    @property
    def total_debt(self):
        total = 0
        for sale in self.sales.all():
            total += max(0, sale.total_price - sale.paid_amount)
        return total

    @property
    def has_debt(self):
        return self.total_debt > 0


class Lead(models.Model):
    STATUS_NEW = 'new'
    STATUS_THINKING = 'thinking'
    STATUS_CALLBACK = 'callback'
    STATUS_NEGOTIATION = 'negotiation'
    STATUS_BOOKED = 'booked'
    STATUS_BOUGHT = 'bought'
    STATUS_REFUSED = 'refused'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_THINKING, 'Думает'),
        (STATUS_CALLBACK, 'Перезвонить'),
        (STATUS_NEGOTIATION, 'Переговоры'),
        (STATUS_BOOKED, 'Забронировал'),
        (STATUS_BOUGHT, 'Купил'),
        (STATUS_REFUSED, 'Отказался'),
    ]

    STATUS_COLORS = {
        STATUS_NEW: 'primary',
        STATUS_THINKING: 'info',
        STATUS_CALLBACK: 'warning',
        STATUS_NEGOTIATION: 'secondary',
        STATUS_BOOKED: 'warning',
        STATUS_BOUGHT: 'success',
        STATUS_REFUSED: 'danger',
    }

    SOURCE_CHOICES = [
        ('office', 'Офис'),
        ('call', 'Звонок'),
        ('instagram', 'Instagram'),
        ('referral', 'Знакомые'),
        ('advertising', 'Реклама'),
        ('website', 'Сайт'),
        ('other', 'Другое'),
    ]

    name = models.CharField(max_length=200, verbose_name='Имя')
    phone = models.CharField(max_length=25, verbose_name='Телефон')
    interested_in = models.CharField(max_length=200, blank=True, verbose_name='Интерес')
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Бюджет ($)')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other', verbose_name='Источник')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, verbose_name='Статус')
    next_contact_date = models.DateField(null=True, blank=True, verbose_name='Следующий контакт')
    note = models.TextField(blank=True, verbose_name='Примечание')
    assigned_to = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leads', verbose_name='Ответственный'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Лид'
        verbose_name_plural = 'Лиды (потенциальные покупатели)'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')

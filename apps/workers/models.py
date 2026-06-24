from django.db import models
from django.utils import timezone
from decimal import Decimal


class Position(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Должность')

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название бригады')
    complex = models.ForeignKey(
        'complex.Complex', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='teams', verbose_name='Объект'
    )
    note = models.TextField(blank=True, verbose_name='Примечание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Бригада'
        verbose_name_plural = 'Бригады'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def active_count(self):
        return self.workers.filter(is_active=True).count()


class Worker(models.Model):
    SALARY_DAILY = 'daily'
    SALARY_MONTHLY = 'monthly'
    SALARY_CHOICES = [
        (SALARY_DAILY, 'Поденно'),
        (SALARY_MONTHLY, 'Ежемесячно'),
    ]

    full_name = models.CharField(max_length=200, verbose_name='ФИО', db_index=True)
    phone = models.CharField(max_length=25, blank=True, verbose_name='Телефон')
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='workers', verbose_name='Должность'
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='workers', verbose_name='Бригада'
    )
    salary_type = models.CharField(
        max_length=10, choices=SALARY_CHOICES,
        default=SALARY_DAILY, verbose_name='Тип зарплаты'
    )
    salary_rate = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Ставка ($)'
    )
    hired_date = models.DateField(default=timezone.now, verbose_name='Дата найма')
    fired_date = models.DateField(null=True, blank=True, verbose_name='Дата увольнения')
    is_active = models.BooleanField(default=True, verbose_name='Активный', db_index=True)
    passport_number = models.CharField(max_length=50, blank=True, verbose_name='Паспорт')
    address = models.TextField(blank=True, verbose_name='Адрес')
    note = models.TextField(blank=True, verbose_name='Примечание')
    added_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='added_workers', verbose_name='Добавил'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Рабочий'
        verbose_name_plural = 'Рабочие'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def position_name(self):
        return self.position.name if self.position else '—'

    @property
    def team_name(self):
        return self.team.name if self.team else '—'


class Attendance(models.Model):
    STATUS_PRESENT = 'present'
    STATUS_ABSENT = 'absent'
    STATUS_HALF = 'half'
    STATUS_SICK = 'sick'

    STATUS_CHOICES = [
        (STATUS_PRESENT, 'Присутствует'),
        (STATUS_ABSENT, 'Отсутствует'),
        (STATUS_HALF, 'Полдня'),
        (STATUS_SICK, 'Болен'),
    ]

    STATUS_COEFFICIENTS = {
        STATUS_PRESENT: Decimal('1.0'),
        STATUS_ABSENT: Decimal('0.0'),
        STATUS_HALF: Decimal('0.5'),
        STATUS_SICK: Decimal('0.0'),
    }

    STATUS_COLORS = {
        STATUS_PRESENT: 'success',
        STATUS_ABSENT: 'danger',
        STATUS_HALF: 'warning',
        STATUS_SICK: 'info',
    }

    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE,
        related_name='attendances', verbose_name='Рабочий'
    )
    date = models.DateField(verbose_name='Дата', db_index=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default=STATUS_PRESENT, verbose_name='Статус'
    )
    note = models.TextField(blank=True, verbose_name='Примечание')
    recorded_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        verbose_name='Записал'
    )

    class Meta:
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
        unique_together = ['worker', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.worker.full_name} — {self.date} — {self.get_status_display()}'

    @property
    def coefficient(self):
        return self.STATUS_COEFFICIENTS.get(self.status, Decimal('0'))

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')


class SalaryPayment(models.Model):
    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE,
        related_name='salary_payments', verbose_name='Рабочий'
    )
    period_start = models.DateField(verbose_name='Начало периода')
    period_end = models.DateField(verbose_name='Конец периода')
    days_worked = models.IntegerField(default=0, verbose_name='Отработано дней')
    base_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Базовая сумма ($)'
    )
    bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Бонус ($)'
    )
    penalty = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name='Штраф ($)'
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Итого ($)'
    )
    is_paid = models.BooleanField(default=False, verbose_name='Выплачено', db_index=True)
    paid_date = models.DateField(null=True, blank=True, verbose_name='Дата выплаты')
    paid_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='salary_payments_made', verbose_name='Выплатил'
    )
    note = models.TextField(blank=True, verbose_name='Примечание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Выплата зарплаты'
        verbose_name_plural = 'Выплаты зарплат'
        ordering = ['-period_end']

    def __str__(self):
        return f'{self.worker.full_name} — {self.period_start:%d.%m.%Y}–{self.period_end:%d.%m.%Y}'

    def save(self, *args, **kwargs):
        self.total_amount = self.base_amount + self.bonus - self.penalty
        super().save(*args, **kwargs)

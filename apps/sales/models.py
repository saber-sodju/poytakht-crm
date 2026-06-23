from django.db import models
from django.utils import timezone


class Booking(models.Model):
    apartment = models.OneToOneField(
        'complex.Apartment', on_delete=models.CASCADE,
        related_name='booking', verbose_name='Квартира'
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE,
        related_name='bookings', verbose_name='Клиент'
    )
    start_date = models.DateField(default=timezone.now, verbose_name='Дата брони')
    end_date = models.DateField(verbose_name='Дата окончания брони')
    deposit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Задаток ($)')
    note = models.TextField(blank=True, verbose_name='Примечание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        verbose_name='Оформил'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']

    def __str__(self):
        return f'Бронь: {self.apartment} → {self.client}'

    @property
    def is_expired(self):
        return self.end_date < timezone.now().date() and self.is_active

    @property
    def days_left(self):
        delta = self.end_date - timezone.now().date()
        return delta.days


class Sale(models.Model):
    PAYMENT_FULL = 'full'
    PAYMENT_INSTALLMENT = 'installment'
    PAYMENT_MORTGAGE = 'mortgage'

    PAYMENT_CHOICES = [
        (PAYMENT_FULL, 'Полная оплата'),
        (PAYMENT_INSTALLMENT, 'Рассрочка'),
        (PAYMENT_MORTGAGE, 'Ипотека'),
    ]

    apartment = models.OneToOneField(
        'complex.Apartment', on_delete=models.CASCADE,
        related_name='sale', verbose_name='Квартира'
    )
    client = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE,
        related_name='sales', verbose_name='Клиент'
    )
    total_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Цена продажи ($)')
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Оплачено ($)')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_CHOICES, verbose_name='Тип оплаты')
    contract_number = models.CharField(max_length=100, blank=True, verbose_name='№ договора')
    contract_date = models.DateField(null=True, blank=True, verbose_name='Дата договора')
    sale_date = models.DateField(default=timezone.now, verbose_name='Дата продажи')
    note = models.TextField(blank=True, verbose_name='Примечание')
    created_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        related_name='sales_created', verbose_name='Оформил'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Продажа'
        verbose_name_plural = 'Продажи'
        ordering = ['-sale_date']

    def __str__(self):
        return f'Продажа: {self.apartment} → {self.client}'

    @property
    def remaining_amount(self):
        return max(0, self.total_price - self.paid_amount)

    @property
    def debt(self):
        return self.remaining_amount

    @property
    def is_paid_fully(self):
        return self.paid_amount >= self.total_price

    @property
    def payment_progress(self):
        if self.total_price == 0:
            return 100
        return min(100, int(self.paid_amount / self.total_price * 100))

    def update_paid_amount(self):
        total = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        self.paid_amount = total
        self.save(update_fields=['paid_amount'])

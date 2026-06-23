from django.db import models
from django.utils import timezone


class PaymentSchedule(models.Model):
    sale = models.ForeignKey(
        'sales.Sale', on_delete=models.CASCADE,
        related_name='schedule', verbose_name='Продажа'
    )
    due_date = models.DateField(verbose_name='Дата платежа')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма ($)')
    is_paid = models.BooleanField(default=False, verbose_name='Оплачено')
    paid_date = models.DateField(null=True, blank=True, verbose_name='Дата оплаты')
    note = models.TextField(blank=True, verbose_name='Примечание')

    class Meta:
        verbose_name = 'График платежей'
        verbose_name_plural = 'Графики платежей'
        ordering = ['due_date']

    def __str__(self):
        return f'{self.sale} — {self.due_date} — ${self.amount}'

    @property
    def is_overdue(self):
        return not self.is_paid and self.due_date < timezone.now().date()

    @property
    def is_due_today(self):
        return not self.is_paid and self.due_date == timezone.now().date()


class Payment(models.Model):
    sale = models.ForeignKey(
        'sales.Sale', on_delete=models.CASCADE,
        related_name='payments', verbose_name='Продажа'
    )
    schedule = models.ForeignKey(
        PaymentSchedule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payments', verbose_name='По графику'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма ($)')
    payment_date = models.DateField(default=timezone.now, verbose_name='Дата платежа')
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name='Квитанция')
    note = models.TextField(blank=True, verbose_name='Примечание')
    added_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        verbose_name='Добавил'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']

    def __str__(self):
        return f'${self.amount} — {self.sale.client.full_name} — {self.payment_date}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sale.update_paid_amount()
        if self.schedule:
            self.schedule.is_paid = True
            self.schedule.paid_date = self.payment_date
            self.schedule.save()

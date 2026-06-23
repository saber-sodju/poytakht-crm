from django.contrib import admin
from .models import Payment, PaymentSchedule


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['sale', 'amount', 'payment_date', 'added_by']


@admin.register(PaymentSchedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['sale', 'due_date', 'amount', 'is_paid']
    list_filter = ['is_paid']

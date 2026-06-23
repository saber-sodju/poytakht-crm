from django.contrib import admin
from .models import Booking, Sale


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'client', 'start_date', 'end_date', 'is_active']
    list_filter = ['is_active']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'client', 'total_price', 'paid_amount', 'payment_type', 'sale_date']
    list_filter = ['payment_type']
    search_fields = ['client__full_name', 'apartment__number', 'contract_number']

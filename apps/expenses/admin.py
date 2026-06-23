from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['category', 'amount', 'date', 'block', 'added_by']
    list_filter = ['category', 'block']
    date_hierarchy = 'date'

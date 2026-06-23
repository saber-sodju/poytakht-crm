from django.contrib import admin
from .models import Client, Lead


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'added_by', 'created_at']
    search_fields = ['full_name', 'phone', 'email', 'passport_number']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'status', 'source', 'next_contact_date', 'assigned_to']
    list_filter = ['status', 'source']
    search_fields = ['name', 'phone']

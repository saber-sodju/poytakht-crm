from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_repr', 'ip_address', 'timestamp']
    list_filter = ['action']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'object_repr', 'description', 'ip_address', 'timestamp']
    search_fields = ['user__username', 'object_repr', 'description']
    date_hierarchy = 'timestamp'

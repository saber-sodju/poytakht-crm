from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import AuditLog
from apps.accounts.decorators import director_required


@login_required
@director_required
def audit_list(request):
    q = request.GET.get('q', '')
    action = request.GET.get('action', '')

    logs = AuditLog.objects.select_related('user').all()

    if q:
        logs = logs.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(description__icontains=q) |
            Q(object_repr__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)

    return render(request, 'audit/list.html', {
        'logs': logs[:500],
        'q': q,
        'action': action,
        'action_choices': AuditLog.ACTION_CHOICES,
    })

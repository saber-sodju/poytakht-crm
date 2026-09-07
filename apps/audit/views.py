from datetime import timedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone

from .models import AuditLog
from apps.accounts.decorators import director_or_admin_required
from apps.accounts.models import CustomUser


@login_required
@director_or_admin_required
def audit_list(request):
    """Who did what, when. Filterable by staff member, action, period, plus a
    one-click view of just the destructive actions (deletions/cancellations),
    which is what the owner usually comes here to check."""
    q = request.GET.get('q', '')
    action = request.GET.get('action', '')
    user_id = request.GET.get('user', '')
    period = request.GET.get('period', '')
    critical = request.GET.get('critical', '')

    logs = AuditLog.objects.select_related('user')

    if q:
        logs = logs.filter(
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(description__icontains=q) |
            Q(object_repr__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)
    if user_id.isdigit():
        logs = logs.filter(user_id=int(user_id))
    if critical:
        logs = logs.filter(action__in=[AuditLog.ACTION_DELETE, AuditLog.ACTION_CANCEL])

    days = {'today': 1, 'week': 7, 'month': 30}.get(period)
    if days:
        since = timezone.now() - timedelta(days=days)
        if period == 'today':
            since = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logs = logs.filter(timestamp__gte=since)

    # Counters for the last 24h, so the owner sees at a glance whether
    # anything destructive happened without reading the whole table.
    day_ago = timezone.now() - timedelta(days=1)
    recent = AuditLog.objects.filter(timestamp__gte=day_ago)
    summary = {
        'total': recent.count(),
        'deletions': recent.filter(
            action__in=[AuditLog.ACTION_DELETE, AuditLog.ACTION_CANCEL]
        ).count(),
        'logins': recent.filter(action=AuditLog.ACTION_LOGIN).count(),
    }

    return render(request, 'audit/list.html', {
        'logs': logs[:500],
        'q': q,
        'action': action,
        'selected_user': user_id,
        'period': period,
        'critical': critical,
        'summary': summary,
        'action_choices': AuditLog.ACTION_CHOICES,
        'staff': CustomUser.objects.filter(is_active=True).order_by('first_name', 'username'),
    })

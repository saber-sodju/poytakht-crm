import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse

from .models import CustomUser, Notification
from .forms import LoginForm, UserCreateForm, UserEditForm
from .decorators import director_required, staff_required

logger = logging.getLogger('apps.accounts')


def _get_client_ip(request) -> str:
    """Return the real client IP, safely handling proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        # Take only the first (leftmost) IP — the actual client
        ip = x_forwarded.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip[:45]   # max length for GenericIPAddressField


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    ip = _get_client_ip(request)
    cache_key = f'login_attempts:{ip}'
    max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
    lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
    lockout_seconds = lockout_minutes * 60

    # Check if this IP is locked out
    attempts = cache.get(cache_key, 0)
    if attempts >= max_attempts:
        logger.warning('Login locked out for IP %s (%d attempts)', ip, attempts)
        return render(request, 'auth/login.html', {
            'form': LoginForm(),
            'locked': True,
            'lockout_minutes': lockout_minutes,
        })

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            cache.delete(cache_key)     # reset attempts on success
            logger.info('User %s logged in from %s', user.username, ip)
            next_url = request.GET.get('next', '')
            # Guard against open redirect: only allow relative URLs
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('dashboard:index')
        else:
            # Increment failed attempt counter
            new_count = attempts + 1
            cache.set(cache_key, new_count, lockout_seconds)
            remaining = max_attempts - new_count
            if remaining > 0:
                messages.warning(
                    request,
                    f'Неверный логин или пароль. Осталось попыток: {remaining}.'
                )
            else:
                logger.warning(
                    'Login locked out for IP %s after %d failed attempts', ip, new_count
                )
                messages.error(
                    request,
                    f'Слишком много неудачных попыток. '
                    f'Доступ заблокирован на {lockout_minutes} минут.'
                )

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
@director_required
def users_list(request):
    users = CustomUser.objects.all().order_by('role', 'last_name')
    return render(request, 'accounts/users.html', {'users': users})


@login_required
@director_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        from apps.audit.models import log_action, AuditLog
        log_action(
            user=request.user, action=AuditLog.ACTION_CREATE,
            model_name='CustomUser', object_id=user.pk,
            object_repr=str(user),
            description=f'Создан пользователь: {user.username} (роль: {user.get_role_display()})',
            request=request,
        )
        messages.success(request, f'Пользователь {user.username} создан.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Новый пользователь'})


@login_required
@director_required
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    old_role = user.role
    form = UserEditForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        if updated.role != old_role:
            from apps.audit.models import log_action, AuditLog
            log_action(
                user=request.user, action=AuditLog.ACTION_UPDATE,
                model_name='CustomUser', object_id=updated.pk,
                object_repr=str(updated),
                description=f'Роль изменена: {old_role} → {updated.role}',
                request=request,
            )
        messages.success(request, 'Пользователь обновлён.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Редактировать: {user.username}',
        'object': user,
    })


@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get('HX-Request'):
        return JsonResponse({'status': 'ok'})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'object': request.user})

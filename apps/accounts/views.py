from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import CustomUser, Notification
from .forms import LoginForm, UserCreateForm, UserEditForm
from .decorators import director_required, staff_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Добро пожаловать, {user.display_name}!')
        return redirect(request.GET.get('next', 'dashboard:index'))
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
        messages.success(request, f'Пользователь {user.username} создан.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Новый пользователь'})


@login_required
@director_required
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = UserEditForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Пользователь обновлён.')
        return redirect('accounts:users')
    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Редактировать: {user.username}', 'object': user})


@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get('HX-Request'):
        return JsonResponse({'status': 'ok'})
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'object': request.user})

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in roles:
                messages.error(request, 'У вас нет доступа к этому разделу.')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def director_required(view_func):
    return role_required('director')(view_func)


def finance_required(view_func):
    return role_required('director', 'admin', 'accountant')(view_func)


def staff_required(view_func):
    return role_required('director', 'admin', 'manager', 'accountant')(view_func)

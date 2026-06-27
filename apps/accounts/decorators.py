from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import CustomUser


def role_required(*roles):
    """Decorator: allows access only if request.user.role is in `roles`."""
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


# ── Single-role shortcuts ──────────────────────────────────────────────────────

def director_required(view_func):
    """Only the Director can access this view."""
    return role_required(CustomUser.ROLE_DIRECTOR)(view_func)


def director_or_admin_required(view_func):
    """Director or Main Admin."""
    return role_required(CustomUser.ROLE_DIRECTOR, CustomUser.ROLE_ADMIN)(view_func)


# ── Finance ───────────────────────────────────────────────────────────────────

def finance_required(view_func):
    """Director, Admin, Accountant — financial data access."""
    return role_required(
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_ACCOUNTANT,
    )(view_func)


# ── Sales & Clients ───────────────────────────────────────────────────────────

def sales_required(view_func):
    """Director, Admin, Manager — create and manage sales/bookings."""
    return role_required(
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_MANAGER,
    )(view_func)


# ── General staff (everyone except warehouse, construction and clients) ────────

def staff_required(view_func):
    """All internal staff: Director, Admin, Manager, Accountant.
    Construction and Warehouse use dedicated decorators for their sections.
    """
    return role_required(
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_MANAGER,
        CustomUser.ROLE_ACCOUNTANT,
    )(view_func)


# ── Construction section ──────────────────────────────────────────────────────

def construction_required(view_func):
    """Director, Admin, Construction Manager — workers & site management."""
    return role_required(
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_CONSTRUCTION,
    )(view_func)


# ── Warehouse / Materials section ─────────────────────────────────────────────

def warehouse_required(view_func):
    """Director, Admin, Construction Manager, Warehouse — materials access."""
    return role_required(
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_CONSTRUCTION,
        CustomUser.ROLE_WAREHOUSE,
    )(view_func)


# ── Combined staff + construction (for cross-role viewing) ────────────────────

def any_staff_required(view_func):
    """Any internal role (excludes client)."""
    return role_required(*CustomUser.STAFF_ROLES)(view_func)

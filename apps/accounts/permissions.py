"""
Object-level permission helpers.

These functions check whether a specific user is allowed to view or modify
a specific database object. Call them from views to enforce data isolation.
"""
from django.core.exceptions import PermissionDenied
from .models import CustomUser


# ── Generic helpers ────────────────────────────────────────────────────────────

def assert_staff(user):
    """Raise PermissionDenied if user is not an internal staff member."""
    if not user.is_authenticated or not user.is_staff_member:
        raise PermissionDenied


def assert_role(user, *roles):
    """Raise PermissionDenied if user's role is not in the given roles."""
    if not user.is_authenticated or user.role not in roles:
        raise PermissionDenied


# ── Client data isolation ──────────────────────────────────────────────────────

def can_view_client(user, client) -> bool:
    """
    Staff can view any client.
    A user with the 'client' role can only view their own Client record.
    """
    if user.role == CustomUser.ROLE_CLIENT:
        # Client users have a linked Client record via OneToOneField on CustomUser
        return hasattr(user, 'client_profile') and user.client_profile == client
    return user.is_staff_member


def assert_can_view_client(user, client):
    if not can_view_client(user, client):
        raise PermissionDenied


def can_view_sale(user, sale) -> bool:
    """
    Finance staff + managers can view any sale.
    A client user can only view their own sale.
    """
    if user.role == CustomUser.ROLE_CLIENT:
        return hasattr(user, 'client_profile') and user.client_profile == sale.client
    return user.is_staff_member


def assert_can_view_sale(user, sale):
    if not can_view_sale(user, sale):
        raise PermissionDenied


def can_view_payment(user, payment) -> bool:
    """
    Finance staff can view any payment.
    A client can only view payments on their own sale.
    """
    if user.role == CustomUser.ROLE_CLIENT:
        return (
            hasattr(user, 'client_profile')
            and user.client_profile == payment.sale.client
        )
    return user.is_staff_member


def assert_can_view_payment(user, payment):
    if not can_view_payment(user, payment):
        raise PermissionDenied


# ── Finance actions ────────────────────────────────────────────────────────────

def can_add_payment(user) -> bool:
    return user.role in (
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_ACCOUNTANT,
    )


def can_delete_payment(user) -> bool:
    """Only directors can delete payments (soft-delete style)."""
    return user.role == CustomUser.ROLE_DIRECTOR


def can_edit_expense(user) -> bool:
    return user.role in (
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_ACCOUNTANT,
    )


# ── Sales actions ──────────────────────────────────────────────────────────────

def can_create_sale(user) -> bool:
    return user.role in (
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_MANAGER,
    )


def can_cancel_sale(user) -> bool:
    """Cancelling a sale requires director or admin approval."""
    return user.role in (CustomUser.ROLE_DIRECTOR, CustomUser.ROLE_ADMIN)


def can_change_apartment_price(user) -> bool:
    """Changing price on an already-sold apartment requires director approval."""
    return user.role == CustomUser.ROLE_DIRECTOR


# ── User management ────────────────────────────────────────────────────────────

def can_manage_user(actor, target_user) -> bool:
    """Director can manage all users except other directors (safety)."""
    if actor.role != CustomUser.ROLE_DIRECTOR:
        return False
    # Prevent non-superusers from demoting/removing other directors
    if target_user.role == CustomUser.ROLE_DIRECTOR and not actor.is_superuser:
        return actor == target_user  # can only edit yourself
    return True


# ── Construction section ───────────────────────────────────────────────────────

def can_access_workers(user) -> bool:
    return user.role in (
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_CONSTRUCTION,
    )


def can_access_materials(user) -> bool:
    return user.role in (
        CustomUser.ROLE_DIRECTOR,
        CustomUser.ROLE_ADMIN,
        CustomUser.ROLE_CONSTRUCTION,
        CustomUser.ROLE_WAREHOUSE,
    )

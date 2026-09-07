"""
Client business logic.

Same service-layer pattern as apps/sales/services.py and
apps/complex/services.py: mutating operations live here, wrapped in
transaction.atomic(), and they never quietly destroy financial history.
"""
import logging

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.audit.models import log_action, AuditLog
from apps.accounts.notifications import notify_management

logger = logging.getLogger('apps.clients')


@transaction.atomic
def delete_client(*, user, client, request=None):
    """
    Delete a client record.

    Refused if the client has ever been party to a sale or a booking —
    including cancelled ones. Those records carry money and are kept
    permanently, and Sale.client is a CASCADE FK, so deleting such a client
    would take the sales and their payments with it.

    What this is for: a client typed in by mistake or entered twice. Real
    buyers stay.
    """
    sales = client.sales.count()
    bookings = client.bookings.count()
    if sales or bookings:
        parts = []
        if sales:
            parts.append(f'продаж: {sales}')
        if bookings:
            parts.append(f'броней: {bookings}')
        raise ValidationError(
            f'Нельзя удалить клиента «{client.full_name}» — за ним закреплены '
            f'{", ".join(parts)}. Если сделка сорвалась, отмените продажу — '
            f'история при этом сохранится.'
        )

    name = client.full_name
    phone = client.phone
    client_pk = client.pk
    client.delete()

    log_action(
        user=user,
        action=AuditLog.ACTION_DELETE,
        model_name='Client',
        object_id=client_pk,
        object_repr=name,
        description=f'Удалён клиент: {name} ({phone})',
        old_value=f'full_name={name}, phone={phone}',
        request=request,
    )
    notify_management(
        notification_type='record_deleted',
        title=f'Удалён клиент: {name}',
        message=f'Удалил: {user.display_name}. Телефон: {phone}. Сделок за клиентом не числилось.',
        link='/clients/',
        exclude_user=user,
    )
    logger.info('Client %s (%s) deleted by %s', client_pk, name, user)

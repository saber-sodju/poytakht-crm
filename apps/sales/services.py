"""
Sale and Booking business logic.

All mutating operations are performed here, NOT in views.
Every function that changes the state of an apartment, booking, or sale
uses transaction.atomic() to prevent partial writes.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.complex.models import Apartment
from apps.audit.models import log_action, AuditLog
from .models import Sale, Booking

logger = logging.getLogger('apps.sales')


@transaction.atomic
def create_booking(*, user, apartment_id, client, start_date, end_date,
                   deposit=Decimal('0'), note='') -> Booking:
    """
    Atomically create a Booking for an apartment.
    Raises ValidationError if the apartment is not free.
    """
    # Lock the row to prevent concurrent bookings of the same apartment
    apartment = Apartment.objects.select_for_update().get(pk=apartment_id)

    if apartment.status != Apartment.STATUS_FREE:
        raise ValidationError(
            f'Квартира {apartment.number} недоступна для бронирования '
            f'(статус: {apartment.get_status_display()}).'
        )

    booking = Booking.objects.create(
        apartment=apartment,
        client=client,
        start_date=start_date,
        end_date=end_date,
        deposit=deposit,
        note=note,
        created_by=user,
    )

    apartment.status = Apartment.STATUS_BOOKED
    apartment.save(update_fields=['status'])

    log_action(
        user=user,
        action=AuditLog.ACTION_CREATE,
        model_name='Booking',
        object_id=booking.pk,
        object_repr=str(booking),
        description=f'Бронирование квартиры {apartment.number} для {client.full_name}',
    )

    logger.info('Booking %d created: apartment %s → client %s', booking.pk, apartment.number, client)
    return booking


@transaction.atomic
def cancel_booking(*, user, booking) -> None:
    """
    Cancel a booking and return the apartment to 'free' status.
    """
    if not booking.is_active:
        raise ValidationError('Это бронирование уже отменено.')

    booking.is_active = False
    booking.save(update_fields=['is_active'])

    apartment = Apartment.objects.select_for_update().get(pk=booking.apartment_id)
    apartment.status = Apartment.STATUS_FREE
    apartment.save(update_fields=['status'])

    log_action(
        user=user,
        action=AuditLog.ACTION_DELETE,
        model_name='Booking',
        object_id=booking.pk,
        object_repr=str(booking),
        description=f'Бронирование отменено: квартира {apartment.number}',
    )

    logger.info('Booking %d cancelled by %s', booking.pk, user)


@transaction.atomic
def create_sale(*, user, apartment_id, client, total_price, payment_type,
                contract_number='', contract_date=None, sale_date=None, note='') -> Sale:
    """
    Atomically create a Sale.

    Validates:
    - Apartment is not already sold
    - No active (non-cancelled) sale exists for this apartment
    - Updates apartment status → sold
    - Closes any existing booking
    - Logs the action
    """
    # Lock apartment to prevent race-condition double-sales
    apartment = Apartment.objects.select_for_update().get(pk=apartment_id)

    if apartment.status == Apartment.STATUS_SOLD:
        raise ValidationError(f'Квартира {apartment.number} уже продана.')

    if apartment.status == Apartment.STATUS_UNAVAILABLE:
        raise ValidationError(f'Квартира {apartment.number} недоступна для продажи.')

    # Belt-and-suspenders: check the Sale table directly
    if Sale.objects.filter(apartment=apartment, is_cancelled=False).exists():
        raise ValidationError(
            f'Для квартиры {apartment.number} уже существует активная продажа.'
        )

    sale = Sale.objects.create(
        apartment=apartment,
        client=client,
        total_price=total_price,
        payment_type=payment_type,
        contract_number=contract_number,
        contract_date=contract_date,
        sale_date=sale_date or timezone.now().date(),
        note=note,
        created_by=user,
    )

    apartment.status = Apartment.STATUS_SOLD
    apartment.save(update_fields=['status'])

    # Close any existing booking for this apartment
    try:
        booking = apartment.booking
        if booking.is_active:
            booking.is_active = False
            booking.save(update_fields=['is_active'])
    except Booking.DoesNotExist:
        pass

    log_action(
        user=user,
        action=AuditLog.ACTION_CREATE,
        model_name='Sale',
        object_id=sale.pk,
        object_repr=str(sale),
        description=(
            f'Продажа квартиры {apartment.number} для {client.full_name}, '
            f'цена: ${total_price}, тип: {payment_type}'
        ),
    )

    logger.info('Sale %d created: apartment %s → client %s by %s', sale.pk, apartment.number, client, user)
    return sale


@transaction.atomic
def cancel_sale(*, user, sale, reason='') -> None:
    """
    Soft-cancel a sale. The record is never deleted.
    The apartment is returned to 'free' status.
    Only directors and admins can call this.
    """
    from apps.accounts.permissions import can_cancel_sale
    if not can_cancel_sale(user):
        raise PermissionError('Только директор или администратор может отменить продажу.')

    if sale.is_cancelled:
        raise ValidationError('Эта продажа уже отменена.')

    old_repr = str(sale)
    sale.is_cancelled = True
    sale.cancelled_at = timezone.now()
    sale.cancelled_by = user
    sale.cancellation_reason = reason
    sale.save(update_fields=[
        'is_cancelled', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'updated_at'
    ])

    apartment = Apartment.objects.select_for_update().get(pk=sale.apartment_id)
    apartment.status = Apartment.STATUS_FREE
    apartment.save(update_fields=['status'])

    log_action(
        user=user,
        action=AuditLog.ACTION_CANCEL,
        model_name='Sale',
        object_id=sale.pk,
        object_repr=old_repr,
        description=f'Продажа отменена. Причина: {reason or "не указана"}',
        old_value=f'is_cancelled=False, apartment.status=sold',
        new_value=f'is_cancelled=True, apartment.status=free, reason={reason}',
    )

    logger.info('Sale %d cancelled by %s. Reason: %s', sale.pk, user, reason)

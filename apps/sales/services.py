"""
Sale and Booking business logic.

All mutating operations are performed here, NOT in views.
Every function that changes the state of an apartment, booking, or sale
uses transaction.atomic() to prevent partial writes.
"""
import logging
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
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


def _add_months(d, months):
    """Same calendar day N months on, clamped to the month's length
    (31 Jan + 1 month -> 28/29 Feb)."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@transaction.atomic
def build_payment_schedule(*, sale, months, start_date=None):
    """
    Split what's left after the down payment into `months` equal monthly
    instalments and write them as PaymentSchedule rows.

    The down payment is already recorded as a real Payment, so it's counted
    in sale.paid_amount — the schedule covers total_price minus what's been
    paid, never the full price. Instalments are rounded to cents and the
    LAST one absorbs the rounding remainder, so the rows add up to the debt
    exactly instead of leaving a few phantom cents outstanding forever.

    Returns the created PaymentSchedule rows.
    """
    from apps.payments.models import PaymentSchedule

    remaining = (sale.total_price - sale.paid_amount).quantize(Decimal('0.01'))
    if remaining <= 0 or not months or months < 1:
        return []

    start = start_date or sale.sale_date
    monthly = (remaining / months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    rows = []
    for m in range(1, months + 1):
        amount = monthly if m < months else (remaining - monthly * (months - 1))
        rows.append(PaymentSchedule(
            sale=sale,
            due_date=_add_months(start, m),
            amount=amount,
        ))
    PaymentSchedule.objects.bulk_create(rows)
    return rows


@transaction.atomic
def create_sale(*, user, apartment_id, client, total_price, payment_type,
                contract_number='', contract_date=None, sale_date=None, note='',
                initial_payment=None, installment_months=None) -> Sale:
    """
    Atomically create a Sale.

    Validates:
    - Apartment is not already sold
    - No active (non-cancelled) sale exists for this apartment
    - initial_payment (if given) does not exceed total_price
    - Updates apartment status → sold
    - Closes any existing booking
    - Creates the first Payment when initial_payment > 0
    - Builds the monthly payment schedule for instalments/mortgages
    - Notifies directors
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

    # First payment / advance — recorded as a real Payment so income = actual money
    if initial_payment and initial_payment > 0:
        if initial_payment > total_price:
            raise ValidationError('Первый платёж не может быть больше цены продажи.')
        from apps.payments.models import Payment
        payment = Payment.objects.create(
            sale=sale,
            amount=initial_payment,
            payment_date=sale.sale_date,
            note='Первый платёж при оформлении продажи',
            added_by=user,
        )  # Payment.save() updates sale.paid_amount automatically
        log_action(
            user=user,
            action=AuditLog.ACTION_CREATE,
            model_name='Payment',
            object_id=payment.pk,
            object_repr=str(payment),
            description=f'Первый платёж ${initial_payment} при продаже квартиры {apartment.number}',
            new_value=f'amount={initial_payment}, sale_id={sale.pk}',
        )

    # Instalment / mortgage: split the outstanding balance across the agreed
    # number of months. Full payment needs no schedule.
    if installment_months and payment_type in (Sale.PAYMENT_INSTALLMENT, Sale.PAYMENT_MORTGAGE):
        sale.refresh_from_db()  # pick up paid_amount set by the initial Payment
        schedule = build_payment_schedule(sale=sale, months=installment_months)
        if schedule:
            logger.info('Sale %d: %d-month schedule created', sale.pk, len(schedule))

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

    _notify_directors(
        notification_type='new_sale',
        title=f'Новая продажа: кв. {apartment.number} — ${total_price}',
        message=f'Клиент: {client.full_name}. Оформил: {user.display_name}.',
        link=f'/sales/{sale.pk}/',
        exclude_user=user,
    )

    logger.info('Sale %d created: apartment %s → client %s by %s', sale.pk, apartment.number, client, user)
    return sale


def _notify_directors(*, notification_type, title, message='', link='', exclude_user=None):
    """Create a Notification for every director (except the actor)."""
    from apps.accounts.models import CustomUser, Notification
    directors = CustomUser.objects.filter(role=CustomUser.ROLE_DIRECTOR, is_active=True)
    if exclude_user is not None:
        directors = directors.exclude(pk=exclude_user.pk)
    Notification.objects.bulk_create([
        Notification(
            user=d, notification_type=notification_type,
            title=title[:200], message=message, link=link,
        )
        for d in directors
    ])


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

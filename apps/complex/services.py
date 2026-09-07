"""
Complex/Block/Floor/Apartment business logic.

Mirrors the service-layer pattern from apps/sales/services.py: mutating
operations live here, not in views, wrapped in transaction.atomic().
"""
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from apps.audit.models import log_action, AuditLog
from apps.accounts.notifications import notify_management

from .models import Floor, Apartment


def _record_deletion(*, user, model_name, obj_id, label, detail, request=None):
    """Every structural deletion goes to the audit log and pings management —
    the owner should never learn from a gap in the data that a block or a
    dozen apartments disappeared."""
    log_action(
        user=user, action=AuditLog.ACTION_DELETE,
        model_name=model_name, object_id=obj_id, object_repr=label,
        description=detail, request=request,
    )
    notify_management(
        notification_type='record_deleted',
        title=f'Удалено: {label}',
        message=f'{detail} Удалил: {user.display_name}.' if user else detail,
        link='/complex/',
        exclude_user=user,
    )


@transaction.atomic
def create_floors(*, block, count):
    """
    Create floors 1..count for `block`. Floors that already exist are left
    alone, so re-running only fills the gaps. Floors start out empty —
    apartments come from copy_floor_layout() or the single-apartment form.

    Returns the list of floor numbers actually created.
    """
    created = []
    for number in range(1, count + 1):
        floor, was_created = Floor.objects.get_or_create(block=block, number=number)
        if was_created:
            created.append(number)
    return created


@transaction.atomic
def copy_floor_layout(*, source_floor, target_numbers, price_step_per_floor=Decimal('0')):
    """
    Replicate the apartment composition of `source_floor` onto every floor
    number in `target_numbers` (within the same block).

    This is the real-world pattern: a tower has one typical floor plan — say
    two 1-room, one 2-room and one 3-room flat — repeated up the building.
    You lay out one floor by hand, then copy it, instead of describing every
    apartment 12 times, or pretending every flat in the block is identical.

    - Each copy keeps the source apartment's type and area.
    - price_per_sqm is shifted by price_step_per_floor for every floor of
      difference from the source (higher floors usually cost more); pass 0
      to price every floor the same. total_price is recomputed from the
      resulting price, never copied blindly.
    - Numbers are assigned as "<floor><position>" (floor 5 -> 501, 502...),
      skipping numbers already taken on that floor, so copying twice tops a
      floor up instead of creating duplicates.
    - Only the layout is copied. Status/sales/clients never are: every new
      apartment starts free.

    Returns the list of created apartment numbers.
    """
    block = source_floor.block
    source_apartments = list(source_floor.apartments.order_by('number', 'pk'))
    created = []

    for floor_number in target_numbers:
        if floor_number == source_floor.number:
            continue  # never copy a floor onto itself

        floor, _ = Floor.objects.get_or_create(block=block, number=floor_number)
        existing_numbers = set(floor.apartments.values_list('number', flat=True))
        floor_gap = floor_number - source_floor.number

        position = 1
        for source_apt in source_apartments:
            # find the next free "<floor><NN>" slot on this floor
            while f'{floor_number}{position:02d}' in existing_numbers:
                position += 1
            number = f'{floor_number}{position:02d}'

            price_per_sqm = source_apt.price_per_sqm + (price_step_per_floor * floor_gap)
            if price_per_sqm < 0:
                price_per_sqm = Decimal('0')

            Apartment.objects.create(
                floor=floor,
                number=number,
                apartment_type=source_apt.apartment_type,
                area=source_apt.area,
                price_per_sqm=price_per_sqm,
                total_price=source_apt.area * price_per_sqm,
                description=source_apt.description,
            )
            existing_numbers.add(number)
            created.append(number)
            position += 1

    return created


# ── Deletion, guarded against destroying financial history ───────────────────
#
# Sale/Payment are never hard-deleted anywhere in this app (Sale has a soft
# `is_cancelled` flag instead — see apps/sales/services.py). Apartment→Sale
# and Sale→Payment are CASCADE FKs, so deleting an Apartment/Floor/Block/
# Complex would silently wipe real sales and payment records underneath it.
# These functions block that: deletion is only allowed when nothing sold or
# booked has ever touched the apartments in scope.

def _apartment_has_history(apartment) -> bool:
    from apps.sales.models import Sale, Booking
    return (
        Sale.objects.filter(apartment=apartment).exists()
        or Booking.objects.filter(apartment=apartment).exists()
    )


def _blocking_apartment_numbers(apartments_qs):
    from apps.sales.models import Sale, Booking
    apt_ids = list(apartments_qs.values_list('pk', flat=True))
    blocked_ids = set(Sale.objects.filter(apartment_id__in=apt_ids).values_list('apartment_id', flat=True))
    blocked_ids |= set(Booking.objects.filter(apartment_id__in=apt_ids).values_list('apartment_id', flat=True))
    if not blocked_ids:
        return []
    return list(
        Apartment.objects.filter(pk__in=blocked_ids).values_list('number', flat=True)
    )


@transaction.atomic
def delete_apartment(apartment, *, user=None, request=None):
    if _apartment_has_history(apartment):
        raise ValidationError(
            f'Квартиру {apartment.number} нельзя удалить — по ней есть история продаж или броней.'
        )
    label = f'{apartment.unit_label} {apartment.number}'
    detail = f'{label} ({apartment.block.name}, этаж {apartment.floor.number}).'
    apt_id = apartment.pk
    apartment.delete()
    if user:
        _record_deletion(user=user, model_name='Apartment', obj_id=apt_id,
                         label=label, detail=detail, request=request)


@transaction.atomic
def delete_floor(floor, *, user=None, request=None):
    blocked = _blocking_apartment_numbers(floor.apartments.all())
    if blocked:
        raise ValidationError(
            f'Этаж {floor.number} нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    label = f'Этаж {floor.number} ({floor.block.name})'
    detail = f'{label}, вместе с квартирами: {floor.apartments.count()}.'
    floor_id = floor.pk
    floor.delete()
    if user:
        _record_deletion(user=user, model_name='Floor', obj_id=floor_id,
                         label=label, detail=detail, request=request)


@transaction.atomic
def delete_block(block, *, user=None, request=None):
    blocked = _blocking_apartment_numbers(Apartment.objects.filter(floor__block=block))
    if blocked:
        raise ValidationError(
            f'Блок «{block.name}» нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    label = f'Блок «{block.name}»'
    detail = (f'{label} комплекса «{block.complex.name}», '
              f'этажей: {block.floors.count()}, квартир: {block.total_apartments}.')
    block_id = block.pk
    block.delete()
    if user:
        _record_deletion(user=user, model_name='Block', obj_id=block_id,
                         label=label, detail=detail, request=request)


@transaction.atomic
def delete_complex(complex_obj, *, user=None, request=None):
    blocked = _blocking_apartment_numbers(Apartment.objects.filter(floor__block__complex=complex_obj))
    if blocked:
        raise ValidationError(
            f'Комплекс «{complex_obj.name}» нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    label = f'Комплекс «{complex_obj.name}»'
    detail = (f'{label}, блоков: {complex_obj.blocks.count()}, '
              f'квартир: {complex_obj.total_apartments}.')
    cx_id = complex_obj.pk
    complex_obj.delete()
    if user:
        _record_deletion(user=user, model_name='Complex', obj_id=cx_id,
                         label=label, detail=detail, request=request)

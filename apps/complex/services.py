"""
Complex/Block/Floor/Apartment business logic.

Mirrors the service-layer pattern from apps/sales/services.py: mutating
operations live here, not in views, wrapped in transaction.atomic().
"""
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Floor, Apartment


@transaction.atomic
def bulk_generate_apartments(*, block, floor_from, floor_to, apartments_per_floor,
                              apartment_type, area, price_per_sqm, start_index=1):
    """
    Create any missing floors in [floor_from, floor_to] for `block`, then
    generate `apartments_per_floor` apartments on each one.

    Apartment numbers are auto-assigned as "<floor><index>" (e.g. 101, 102...)
    starting at `start_index`; numbers already used on a floor are skipped,
    so calling this again on the same block only fills in the gaps instead
    of creating duplicates. Every generated apartment gets the same type/
    area/price and starts out STATUS_FREE — individual apartments can be
    corrected afterwards via the normal apartment edit form.

    Returns the list of created apartment numbers.
    """
    total_price = area * price_per_sqm
    created = []

    for floor_number in range(floor_from, floor_to + 1):
        floor, _ = Floor.objects.get_or_create(block=block, number=floor_number)
        existing_numbers = set(floor.apartments.values_list('number', flat=True))

        idx = start_index
        made = 0
        while made < apartments_per_floor:
            candidate = f'{floor_number}{idx:02d}'
            if candidate not in existing_numbers:
                Apartment.objects.create(
                    floor=floor,
                    number=candidate,
                    apartment_type=apartment_type,
                    area=area,
                    price_per_sqm=price_per_sqm,
                    total_price=total_price,
                )
                existing_numbers.add(candidate)
                created.append(candidate)
                made += 1
            idx += 1

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
def delete_apartment(apartment):
    if _apartment_has_history(apartment):
        raise ValidationError(
            f'Квартиру {apartment.number} нельзя удалить — по ней есть история продаж или броней.'
        )
    apartment.delete()


@transaction.atomic
def delete_floor(floor):
    blocked = _blocking_apartment_numbers(floor.apartments.all())
    if blocked:
        raise ValidationError(
            f'Этаж {floor.number} нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    floor.delete()


@transaction.atomic
def delete_block(block):
    blocked = _blocking_apartment_numbers(Apartment.objects.filter(floor__block=block))
    if blocked:
        raise ValidationError(
            f'Блок «{block.name}» нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    block.delete()


@transaction.atomic
def delete_complex(complex_obj):
    blocked = _blocking_apartment_numbers(Apartment.objects.filter(floor__block__complex=complex_obj))
    if blocked:
        raise ValidationError(
            f'Комплекс «{complex_obj.name}» нельзя удалить — есть квартиры с историей продаж/броней: {", ".join(blocked)}.'
        )
    complex_obj.delete()

"""
Complex/Block/Floor/Apartment business logic.

Mirrors the service-layer pattern from apps/sales/services.py: mutating
operations live here, not in views, wrapped in transaction.atomic().
"""
from django.db import transaction

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

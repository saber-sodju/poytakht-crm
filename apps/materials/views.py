from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from datetime import date

from .models import Supplier, Material, MaterialMovement
from apps.accounts.decorators import staff_required, construction_required, warehouse_required


@login_required
@warehouse_required
def material_list(request):
    q = request.GET.get('q', '')
    low_stock = request.GET.get('low', '')

    materials = Material.objects.select_related('supplier').all()
    if q:
        materials = materials.filter(Q(name__icontains=q))
    if low_stock:
        from django.db.models import F
        materials = materials.filter(quantity__lte=F('min_quantity'), min_quantity__gt=0)

    total_value = sum(m.total_value for m in materials)
    low_count = Material.objects.filter(
        min_quantity__gt=0
    ).extra(where=["quantity <= min_quantity"]).count()

    context = {
        'materials': materials,
        'q': q,
        'low_stock': low_stock,
        'total_value': total_value,
        'low_count': low_count,
    }
    return render(request, 'materials/list.html', context)


@login_required
@warehouse_required
def material_detail(request, pk):
    material = get_object_or_404(Material.objects.select_related('supplier'), pk=pk)
    movements = material.movements.select_related('supplier', 'block', 'added_by').order_by('-date')[:50]
    total_in = material.movements.filter(direction='in').aggregate(t=Sum('quantity'))['t'] or 0
    total_out = material.movements.filter(direction='out').aggregate(t=Sum('quantity'))['t'] or 0
    return render(request, 'materials/detail.html', {
        'material': material,
        'movements': movements,
        'total_in': total_in,
        'total_out': total_out,
    })


@login_required
@construction_required
def material_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        unit = request.POST.get('unit', 'piece')
        min_quantity = Decimal(request.POST.get('min_quantity', '0') or '0')
        price_per_unit = Decimal(request.POST.get('price_per_unit', '0') or '0')
        supplier_id = request.POST.get('supplier') or None
        note = request.POST.get('note', '')

        if not name:
            messages.error(request, 'Название обязательно.')
        else:
            m = Material.objects.create(
                name=name, unit=unit, min_quantity=min_quantity,
                price_per_unit=price_per_unit, supplier_id=supplier_id, note=note,
            )
            messages.success(request, f'Материал «{name}» добавлен.')
            return redirect('materials:detail', pk=m.pk)

    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'materials/form.html', {
        'suppliers': suppliers,
        'unit_choices': Material.UNIT_CHOICES,
        'title': 'Новый материал',
    })


@login_required
@construction_required
def material_edit(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        material.name = request.POST.get('name', material.name).strip()
        material.unit = request.POST.get('unit', material.unit)
        material.min_quantity = Decimal(request.POST.get('min_quantity', '0') or '0')
        material.price_per_unit = Decimal(request.POST.get('price_per_unit', '0') or '0')
        material.supplier_id = request.POST.get('supplier') or None
        material.note = request.POST.get('note', '')
        material.save()
        messages.success(request, 'Материал обновлён.')
        return redirect('materials:detail', pk=pk)

    suppliers = Supplier.objects.filter(is_active=True)
    return render(request, 'materials/form.html', {
        'material': material,
        'suppliers': suppliers,
        'unit_choices': Material.UNIT_CHOICES,
        'title': 'Редактировать материал',
    })


@login_required
@warehouse_required
def movement_create(request, material_pk=None):
    material = get_object_or_404(Material, pk=material_pk) if material_pk else None

    if request.method == 'POST':
        mat_id = request.POST.get('material')
        direction = request.POST.get('direction', 'in')
        quantity = Decimal(request.POST.get('quantity', '0') or '0')
        price_per_unit = Decimal(request.POST.get('price_per_unit', '0') or '0')
        supplier_id = request.POST.get('supplier') or None
        block_id = request.POST.get('block') or None
        dt = request.POST.get('date') or str(date.today())
        note = request.POST.get('note', '')

        if quantity <= 0:
            messages.error(request, 'Количество должно быть больше нуля.')
        else:
            mat = get_object_or_404(Material, pk=mat_id)
            mv = MaterialMovement(
                material=mat, direction=direction, quantity=quantity,
                price_per_unit=price_per_unit, supplier_id=supplier_id,
                block_id=block_id, date=dt, note=note, added_by=request.user,
            )
            mv.save()
            label = 'Приход' if direction == 'in' else 'Расход'
            messages.success(request, f'{label} {quantity} {mat.get_unit_display()} материала «{mat.name}» записан.')
            return redirect('materials:detail', pk=mat.pk)

    materials = Material.objects.all()
    suppliers = Supplier.objects.filter(is_active=True)
    from apps.complex.models import Block
    blocks = Block.objects.select_related('complex').all()

    return render(request, 'materials/movement_form.html', {
        'material': material,
        'materials': materials,
        'suppliers': suppliers,
        'blocks': blocks,
        'today': date.today(),
        'direction_choices': MaterialMovement.DIRECTION_CHOICES,
    })


@login_required
@warehouse_required
def supplier_list(request):
    suppliers = Supplier.objects.prefetch_related('materials').filter(is_active=True)
    return render(request, 'materials/supplier_list.html', {'suppliers': suppliers})


@login_required
@construction_required
def supplier_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        contact_person = request.POST.get('contact_person', '')
        note = request.POST.get('note', '')
        if not name:
            messages.error(request, 'Название обязательно.')
        else:
            Supplier.objects.create(
                name=name, phone=phone, address=address,
                contact_person=contact_person, note=note,
            )
            messages.success(request, f'Поставщик «{name}» добавлен.')
            return redirect('materials:suppliers')

    return render(request, 'materials/supplier_form.html', {'title': 'Новый поставщик'})


@login_required
@construction_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier.name = request.POST.get('name', supplier.name).strip()
        supplier.phone = request.POST.get('phone', '')
        supplier.address = request.POST.get('address', '')
        supplier.contact_person = request.POST.get('contact_person', '')
        supplier.note = request.POST.get('note', '')
        supplier.save()
        messages.success(request, 'Поставщик обновлён.')
        return redirect('materials:suppliers')

    return render(request, 'materials/supplier_form.html', {
        'supplier': supplier, 'title': 'Редактировать поставщика'
    })

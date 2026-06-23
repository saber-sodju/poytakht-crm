from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse

from .models import Complex, Block, Floor, Apartment, ConstructionStage, PhotoReport
from .forms import ComplexForm, BlockForm, FloorForm, ApartmentForm, ConstructionStageForm, PhotoReportForm
from apps.accounts.decorators import staff_required


@login_required
@staff_required
def complex_list(request):
    complexes = Complex.objects.prefetch_related('blocks__floors__apartments').all()
    return render(request, 'complex/list.html', {'complexes': complexes})


@login_required
@staff_required
def complex_create(request):
    form = ComplexForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        c = form.save()
        messages.success(request, f'Комплекс «{c.name}» создан.')
        return redirect('complex:list')
    return render(request, 'complex/form.html', {'form': form, 'title': 'Новый комплекс'})


@login_required
@staff_required
def complex_detail(request, pk):
    complex_obj = get_object_or_404(Complex, pk=pk)
    blocks = complex_obj.blocks.prefetch_related('floors__apartments').all()
    return render(request, 'complex/detail.html', {'complex': complex_obj, 'blocks': blocks})


@login_required
@staff_required
def block_create(request):
    form = BlockForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        block = form.save()
        messages.success(request, f'Блок «{block.name}» создан.')
        return redirect('complex:complex_detail', pk=block.complex_id)
    return render(request, 'complex/form.html', {'form': form, 'title': 'Новый блок'})


@login_required
@staff_required
def block_detail(request, pk):
    block = get_object_or_404(Block.objects.prefetch_related('floors__apartments'), pk=pk)
    floors = block.floors.prefetch_related('apartments').order_by('-number')
    stats = {
        'total': Apartment.objects.filter(floor__block=block).count(),
        'free': Apartment.objects.filter(floor__block=block, status='free').count(),
        'booked': Apartment.objects.filter(floor__block=block, status='booked').count(),
        'sold': Apartment.objects.filter(floor__block=block, status='sold').count(),
    }
    stages = block.stages.all().order_by('stage')
    return render(request, 'complex/block_detail.html', {
        'block_obj': block, 'floors': floors, 'stats': stats, 'stages': stages
    })


@login_required
@staff_required
def floor_create(request, block_pk):
    block = get_object_or_404(Block, pk=block_pk)
    initial = {'block': block}
    form = FloorForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        floor = form.save()
        messages.success(request, f'Этаж {floor.number} добавлен.')
        return redirect('complex:block_detail', pk=block_pk)
    return render(request, 'complex/form.html', {'form': form, 'title': f'Новый этаж — {block.name}'})


@login_required
@staff_required
def apartment_detail(request, pk):
    apt = get_object_or_404(Apartment, pk=pk)
    sale = getattr(apt, 'sale', None)
    booking = getattr(apt, 'booking', None)
    return render(request, 'complex/apartment_detail.html', {
        'apt': apt, 'sale': sale, 'booking': booking
    })


@login_required
@staff_required
def apartment_create(request, floor_pk=None):
    floor = get_object_or_404(Floor, pk=floor_pk) if floor_pk else None
    initial = {'floor': floor} if floor else {}
    form = ApartmentForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        apt = form.save()
        messages.success(request, f'Квартира {apt.number} добавлена.')
        return redirect('complex:apartment_detail', pk=apt.pk)
    return render(request, 'complex/apartment_form.html', {'form': form, 'title': 'Новая квартира'})


@login_required
@staff_required
def apartment_edit(request, pk):
    apt = get_object_or_404(Apartment, pk=pk)
    form = ApartmentForm(request.POST or None, request.FILES or None, instance=apt)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Квартира обновлена.')
        return redirect('complex:apartment_detail', pk=pk)
    return render(request, 'complex/apartment_form.html', {'form': form, 'title': f'Квартира {apt.number}', 'object': apt})


@login_required
@staff_required
def apartment_api(request, pk):
    apt = get_object_or_404(Apartment, pk=pk)
    sale = getattr(apt, 'sale', None)
    booking = getattr(apt, 'booking', None)
    data = {
        'id': apt.pk,
        'number': apt.number,
        'type': apt.get_apartment_type_display(),
        'area': str(apt.area),
        'price_per_sqm': str(apt.price_per_sqm),
        'total_price': str(apt.total_price),
        'status': apt.status,
        'status_display': apt.get_status_display(),
        'floor': apt.floor.number,
        'block': apt.block.name,
        'detail_url': f'/complex/apartments/{apt.pk}/',
        'client_name': sale.client.full_name if sale else (booking.client.full_name if booking else None),
    }
    return JsonResponse(data)


@login_required
@staff_required
def stage_update(request, block_pk):
    block = get_object_or_404(Block, pk=block_pk)
    stage_key = request.POST.get('stage')
    stage_obj, _ = ConstructionStage.objects.get_or_create(block=block, stage=stage_key)
    form = ConstructionStageForm(request.POST, instance=stage_obj)
    if form.is_valid():
        s = form.save(commit=False)
        s.block = block
        s.save()
        messages.success(request, f'Этап «{s.get_stage_display()}» обновлён.')
    return redirect('complex:block_detail', pk=block_pk)


@login_required
@staff_required
def photo_add(request, block_pk):
    block = get_object_or_404(Block, pk=block_pk)
    form = PhotoReportForm(request.POST or None, request.FILES or None, initial={'block': block})
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.uploaded_by = request.user
        p.save()
        messages.success(request, 'Фотоотчёт добавлен.')
        return redirect('complex:block_detail', pk=block_pk)
    return render(request, 'complex/photo_form.html', {'form': form, 'block': block})

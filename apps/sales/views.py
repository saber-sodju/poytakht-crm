from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Booking, Sale
from .forms import BookingForm, SaleForm
from apps.complex.models import Apartment
from apps.accounts.decorators import staff_required


@login_required
@staff_required
def sale_list(request):
    q = request.GET.get('q', '')
    sales = Sale.objects.select_related('apartment__floor__block', 'client', 'created_by').all()
    if q:
        sales = sales.filter(
            Q(client__full_name__icontains=q) |
            Q(apartment__number__icontains=q) |
            Q(contract_number__icontains=q)
        )
    return render(request, 'sales/list.html', {'sales': sales, 'q': q})


@login_required
@staff_required
def sale_create(request):
    apt_pk = request.GET.get('apt')
    initial = {}
    if apt_pk:
        apt = Apartment.objects.filter(pk=apt_pk).first()
        if apt:
            initial['apartment'] = apt
            initial['total_price'] = apt.total_price

    form = SaleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        sale = form.save(commit=False)
        sale.created_by = request.user
        sale.save()
        sale.apartment.status = Apartment.STATUS_SOLD
        sale.apartment.save()
        if hasattr(sale.apartment, 'booking'):
            booking = sale.apartment.booking
            booking.is_active = False
            booking.save()
        messages.success(request, f'Продажа квартиры {sale.apartment.number} оформлена!')
        return redirect('sales:sale_detail', pk=sale.pk)
    return render(request, 'sales/form.html', {'form': form, 'title': 'Оформить продажу'})


@login_required
@staff_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('apartment__floor__block', 'client', 'created_by')
                    .prefetch_related('payments', 'schedule'),
        pk=pk
    )
    return render(request, 'sales/detail.html', {'sale': sale})


@login_required
@staff_required
def booking_list(request):
    bookings = Booking.objects.select_related('apartment__floor__block', 'client').filter(is_active=True)
    return render(request, 'sales/bookings.html', {'bookings': bookings})


@login_required
@staff_required
def booking_create(request):
    apt_pk = request.GET.get('apt')
    initial = {}
    if apt_pk:
        apt = Apartment.objects.filter(pk=apt_pk, status='free').first()
        if apt:
            initial['apartment'] = apt

    form = BookingForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        booking = form.save(commit=False)
        booking.created_by = request.user
        booking.save()
        booking.apartment.status = Apartment.STATUS_BOOKED
        booking.apartment.save()
        messages.success(request, f'Квартира {booking.apartment.number} забронирована.')
        return redirect('sales:bookings')
    return render(request, 'sales/booking_form.html', {'form': form, 'title': 'Новое бронирование'})


@login_required
@staff_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        booking.is_active = False
        booking.save()
        booking.apartment.status = Apartment.STATUS_FREE
        booking.apartment.save()
        messages.success(request, 'Бронирование отменено.')
        return redirect('sales:bookings')
    return render(request, 'sales/booking_cancel.html', {'booking': booking})

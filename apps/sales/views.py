import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .models import Booking, Sale
from .forms import BookingForm, SaleForm
from .services import (
    create_sale as svc_create_sale,
    cancel_booking as svc_cancel_booking,
    cancel_sale as svc_cancel_sale,
)
from apps.complex.models import Apartment
from apps.clients.models import Client as ClientModel
from apps.accounts.decorators import staff_required, sales_required, director_or_admin_required
from apps.accounts.permissions import assert_can_view_sale

logger = logging.getLogger('apps.sales')


@login_required
@staff_required
def sale_list(request):
    q = request.GET.get('q', '')
    # Non-cancelled sales only (hide soft-deleted)
    sales = (
        Sale.objects
        .select_related('apartment__floor__block', 'client', 'created_by')
        .filter(is_cancelled=False)
    )
    if q:
        sales = sales.filter(
            Q(client__full_name__icontains=q)
            | Q(apartment__number__icontains=q)
            | Q(contract_number__icontains=q)
        )
    return render(request, 'sales/list.html', {'sales': sales, 'q': q})


@login_required
@sales_required
def sale_create(request):
    """
    Create a new Sale using the atomic service function.
    Prevents double-sale via database-level lock.
    """
    apt_pk = request.GET.get('apt')
    initial = {}
    if apt_pk:
        apt = Apartment.objects.filter(pk=apt_pk, status=Apartment.STATUS_FREE).first()
        if apt:
            initial['apartment'] = apt
            initial['total_price'] = apt.total_price

    # coming back from "add client" mid-sale
    client_pk = request.GET.get('client')
    if client_pk:
        client = ClientModel.objects.filter(pk=client_pk).first()
        if client:
            initial['client'] = client

    form = SaleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        try:
            sale = svc_create_sale(
                user=request.user,
                apartment_id=cd['apartment'].pk,
                client=cd['client'],
                total_price=cd['total_price'],
                payment_type=cd['payment_type'],
                contract_number=cd.get('contract_number', ''),
                contract_date=cd.get('contract_date'),
                sale_date=cd.get('sale_date'),
                note=cd.get('note', ''),
                initial_payment=cd.get('initial_payment'),
                installment_months=cd.get('installment_months'),
            )
            messages.success(request, f'Продажа квартиры {sale.apartment.number} оформлена!')
            return redirect('sales:sale_detail', pk=sale.pk)
        except ValidationError as exc:
            messages.error(request, exc.message)

    return render(request, 'sales/form.html', {'form': form, 'title': 'Оформить продажу'})


@login_required
@staff_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects
        .select_related('apartment__floor__block', 'client', 'created_by', 'cancelled_by')
        .prefetch_related('payments', 'schedule'),
        pk=pk,
    )
    # Object-level check: clients can only see their own sale
    assert_can_view_sale(request.user, sale)
    return render(request, 'sales/detail.html', {'sale': sale})


@login_required
@sales_required
def sale_cancel(request, pk):
    """Cancel a sale when the deal falls through.

    Soft-cancel only: the sale, its payments and the audit trail stay; the
    apartment goes back to free and management is notified. Nothing about a
    real transaction is ever erased.
    """
    sale = get_object_or_404(
        Sale.objects.select_related('client', 'apartment__floor__block'), pk=pk
    )
    if sale.is_cancelled:
        messages.warning(request, 'Эта продажа уже отменена.')
        return redirect('sales:sale_detail', pk=pk)

    if request.method == 'POST':
        reason = (request.POST.get('reason') or '').strip()
        try:
            svc_cancel_sale(user=request.user, sale=sale, reason=reason)
        except PermissionError as exc:
            messages.error(request, str(exc))
            return redirect('sales:sale_detail', pk=pk)
        except ValidationError as exc:
            messages.error(request, exc.message)
            return redirect('sales:sale_detail', pk=pk)
        messages.success(
            request,
            f'Продажа отменена, {sale.apartment.unit_label.lower()} '
            f'{sale.apartment.number} снова свободна. Руководство уведомлено.',
        )
        return redirect('sales:sale_detail', pk=pk)

    return render(request, 'sales/sale_cancel.html', {'sale': sale})


@login_required
@staff_required
def booking_list(request):
    bookings = (
        Booking.objects
        .select_related('apartment__floor__block', 'client', 'created_by')
        .filter(is_active=True)
    )
    return render(request, 'sales/bookings.html', {'bookings': bookings})


@login_required
@sales_required
def booking_create(request):
    apt_pk = request.GET.get('apt')
    initial = {}
    if apt_pk:
        apt = Apartment.objects.filter(pk=apt_pk, status=Apartment.STATUS_FREE).first()
        if apt:
            initial['apartment'] = apt

    client_pk = request.GET.get('client')
    if client_pk:
        client = ClientModel.objects.filter(pk=client_pk).first()
        if client:
            initial['client'] = client

    form = BookingForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        try:
            from .services import create_booking as svc_create_booking
            booking = svc_create_booking(
                user=request.user,
                apartment_id=cd['apartment'].pk,
                client=cd['client'],
                start_date=cd['start_date'],
                end_date=cd['end_date'],
                deposit=cd.get('deposit', 0),
                note=cd.get('note', ''),
            )
            messages.success(request, f'Квартира {booking.apartment.number} забронирована.')
            return redirect('sales:bookings')
        except ValidationError as exc:
            messages.error(request, exc.message)

    return render(request, 'sales/booking_form.html', {'form': form, 'title': 'Новое бронирование'})


@login_required
@sales_required
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        try:
            svc_cancel_booking(user=request.user, booking=booking)
            messages.success(request, 'Бронирование отменено.')
        except ValidationError as exc:
            messages.error(request, exc.message)
        return redirect('sales:bookings')
    return render(request, 'sales/booking_cancel.html', {'booking': booking})

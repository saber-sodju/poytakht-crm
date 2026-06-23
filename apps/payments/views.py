from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone

from .models import Payment, PaymentSchedule
from .forms import PaymentForm, ScheduleForm
from apps.accounts.decorators import staff_required, finance_required


@login_required
@staff_required
def payment_list(request):
    q = request.GET.get('q', '')
    payments = Payment.objects.select_related('sale__client', 'sale__apartment', 'added_by').all()
    if q:
        payments = payments.filter(
            Q(sale__client__full_name__icontains=q) |
            Q(sale__apartment__number__icontains=q)
        )
    total = payments.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'payments/list.html', {'payments': payments, 'q': q, 'total': total})


@login_required
@finance_required
def payment_add(request):
    sale_pk = request.GET.get('sale')
    initial = {}
    if sale_pk:
        from apps.sales.models import Sale
        sale = Sale.objects.filter(pk=sale_pk).first()
        if sale:
            initial['sale'] = sale
            initial['amount'] = sale.remaining_amount

    form = PaymentForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        payment = form.save(commit=False)
        payment.added_by = request.user
        payment.save()
        messages.success(request, f'Платёж ${payment.amount} добавлен.')
        return redirect('sales:sale_detail', pk=payment.sale_id)
    return render(request, 'payments/form.html', {'form': form, 'title': 'Добавить платёж'})


@login_required
@staff_required
def overdue_list(request):
    today = timezone.now().date()
    overdue = PaymentSchedule.objects.filter(
        is_paid=False, due_date__lt=today
    ).select_related('sale__client', 'sale__apartment').order_by('due_date')
    total_overdue = overdue.aggregate(total=Sum('amount'))['total'] or 0
    return render(request, 'payments/overdue.html', {'overdue': overdue, 'total_overdue': total_overdue})


@login_required
@staff_required
def upcoming_list(request):
    today = timezone.now().date()
    upcoming = PaymentSchedule.objects.filter(
        is_paid=False, due_date__gte=today
    ).select_related('sale__client', 'sale__apartment').order_by('due_date')[:50]
    return render(request, 'payments/upcoming.html', {'upcoming': upcoming})


@login_required
@finance_required
def schedule_add(request, sale_pk):
    from apps.sales.models import Sale
    sale = get_object_or_404(Sale, pk=sale_pk)
    form = ScheduleForm(request.POST or None, initial={'sale': sale})
    if request.method == 'POST' and form.is_valid():
        s = form.save()
        messages.success(request, f'Платёж по графику {s.due_date} добавлен.')
        return redirect('sales:sale_detail', pk=sale_pk)
    return render(request, 'payments/schedule_form.html', {'form': form, 'sale': sale})

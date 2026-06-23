from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.complex.models import Apartment, Block, Complex
from apps.clients.models import Client, Lead
from apps.sales.models import Sale, Booking
from apps.payments.models import Payment, PaymentSchedule
from apps.expenses.models import Expense
from apps.audit.models import AuditLog


@login_required
def dashboard_index(request):
    if request.user.is_client_role:
        return redirect('dashboard:client_dashboard')

    today = timezone.now().date()
    month_start = today.replace(day=1)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Apartment stats
    apt_stats = {
        'total': Apartment.objects.count(),
        'free': Apartment.objects.filter(status='free').count(),
        'booked': Apartment.objects.filter(status='booked').count(),
        'sold': Apartment.objects.filter(status='sold').count(),
    }

    # Financial stats (current month)
    month_income = Payment.objects.filter(
        payment_date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    month_expenses = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    month_profit = month_income - month_expenses

    # Debts
    total_debt = 0
    clients_with_debt = 0
    for sale in Sale.objects.all():
        debt = sale.remaining_amount
        if debt > 0:
            total_debt += debt
            clients_with_debt += 1

    # Overdue payments
    overdue = PaymentSchedule.objects.filter(
        is_paid=False, due_date__lt=today
    ).count()

    # Today's payments
    today_payments = PaymentSchedule.objects.filter(
        is_paid=False, due_date=today
    ).count()

    # Expiring bookings (within 3 days)
    expiring_bookings = Booking.objects.filter(
        is_active=True, end_date__lte=today + timedelta(days=3), end_date__gte=today
    ).count()

    # Recent actions
    recent_logs = AuditLog.objects.select_related('user').all()[:10]

    # Recent sales (this month)
    recent_sales = Sale.objects.select_related(
        'apartment__floor__block', 'client'
    ).filter(sale_date__gte=month_start).order_by('-sale_date')[:5]

    # Monthly income chart (last 6 months)
    chart_labels = []
    chart_income = []
    chart_expenses = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        m_start = d.replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1)

        inc = Payment.objects.filter(
            payment_date__gte=m_start, payment_date__lt=m_end
        ).aggregate(t=Sum('amount'))['t'] or 0

        exp = Expense.objects.filter(
            date__gte=m_start, date__lt=m_end
        ).aggregate(t=Sum('amount'))['t'] or 0

        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                       'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        chart_labels.append(f'{month_names[m_start.month - 1]} {m_start.year}')
        chart_income.append(float(inc))
        chart_expenses.append(float(exp))

    # Lead stats
    leads_new = Lead.objects.filter(status='new').count()
    leads_callback = Lead.objects.filter(status='callback', next_contact_date=today).count()

    # Block budget status
    blocks = Block.objects.select_related('complex').prefetch_related('expenses').all()

    context = {
        'apt_stats': apt_stats,
        'month_income': month_income,
        'month_expenses': month_expenses,
        'month_profit': month_profit,
        'total_debt': total_debt,
        'clients_with_debt': clients_with_debt,
        'overdue': overdue,
        'today_payments': today_payments,
        'expiring_bookings': expiring_bookings,
        'recent_logs': recent_logs,
        'recent_sales': recent_sales,
        'chart_labels': chart_labels,
        'chart_income': chart_income,
        'chart_expenses': chart_expenses,
        'leads_new': leads_new,
        'leads_callback': leads_callback,
        'blocks': blocks,
        'today': today,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def client_dashboard(request):
    if not request.user.is_client_role:
        return redirect('dashboard:index')
    if hasattr(request.user, 'client_profile'):
        client = request.user.client_profile
        sales = client.sales.prefetch_related('payments', 'schedule').all()
        return render(request, 'dashboard/client.html', {'client': client, 'sales': sales})
    return render(request, 'dashboard/client_no_data.html')


@login_required
def reports_view(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Sales by month
    sales_data = Sale.objects.filter(sale_date__gte=month_start)
    total_sales_count = sales_data.count()
    total_sales_amount = sales_data.aggregate(t=Sum('total_price'))['t'] or 0

    # Expenses by category
    exp_by_cat = {}
    for exp in Expense.objects.all():
        cat = exp.get_category_display()
        exp_by_cat[cat] = exp_by_cat.get(cat, 0) + float(exp.amount)

    # Debts summary
    debt_clients = []
    for sale in Sale.objects.select_related('client', 'apartment').all():
        if sale.remaining_amount > 0:
            debt_clients.append(sale)
    debt_clients.sort(key=lambda s: s.remaining_amount, reverse=True)

    context = {
        'total_sales_count': total_sales_count,
        'total_sales_amount': total_sales_amount,
        'exp_by_cat': exp_by_cat,
        'debt_clients': debt_clients[:20],
        'today': today,
        'month_start': month_start,
    }
    return render(request, 'reports/index.html', context)

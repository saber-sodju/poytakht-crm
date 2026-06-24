from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta, date

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

    # Apartment stats — single query with annotation
    apt_counts = Apartment.objects.aggregate(
        total=Count('id'),
        free=Count('id', filter=Q(status='free')),
        booked=Count('id', filter=Q(status='booked')),
        sold=Count('id', filter=Q(status='sold')),
    )

    # Financial stats — current month
    month_income = Payment.objects.filter(
        payment_date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    month_expenses = Expense.objects.filter(
        date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    month_profit = month_income - month_expenses

    # Total debt — single aggregate instead of loop
    sales_agg = Sale.objects.aggregate(
        total_price=Sum('total_price'),
        total_paid=Sum('paid_amount'),
        count_debt=Count('id', filter=Q(paid_amount__lt=F('total_price')))
    )
    total_debt = max(0, (sales_agg['total_price'] or 0) - (sales_agg['total_paid'] or 0))
    clients_with_debt = sales_agg['count_debt'] or 0

    # Schedule stats
    overdue = PaymentSchedule.objects.filter(is_paid=False, due_date__lt=today).count()
    today_payments = PaymentSchedule.objects.filter(is_paid=False, due_date=today).count()

    # Bookings expiring soon
    expiring_bookings = Booking.objects.filter(
        is_active=True, end_date__lte=today + timedelta(days=3), end_date__gte=today
    ).count()

    # Recent audit logs
    recent_logs = AuditLog.objects.select_related('user').all()[:8]

    # Recent sales
    recent_sales = Sale.objects.select_related(
        'apartment__floor__block', 'client'
    ).filter(sale_date__gte=month_start).order_by('-sale_date')[:5]

    # Monthly chart — 6 months
    MONTH_NAMES = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                   'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    chart_labels, chart_income, chart_expenses_list = [], [], []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        m_start = d.replace(day=1)
        m_end = (m_start.replace(month=m_start.month % 12 + 1, day=1)
                 if m_start.month < 12
                 else m_start.replace(year=m_start.year + 1, month=1, day=1))
        inc = Payment.objects.filter(
            payment_date__gte=m_start, payment_date__lt=m_end
        ).aggregate(t=Sum('amount'))['t'] or 0
        exp = Expense.objects.filter(
            date__gte=m_start, date__lt=m_end
        ).aggregate(t=Sum('amount'))['t'] or 0
        chart_labels.append(f'{MONTH_NAMES[m_start.month - 1]} {m_start.year}')
        chart_income.append(float(inc))
        chart_expenses_list.append(float(exp))

    # Lead stats
    leads_new = Lead.objects.filter(status='new').count()
    leads_callback = Lead.objects.filter(status='callback', next_contact_date=today).count()

    # Blocks with budget info
    blocks = Block.objects.select_related('complex').prefetch_related('expenses').all()

    # Workers stats (if app is installed)
    workers_total = 0
    workers_present_today = 0
    try:
        from apps.workers.models import Worker, Attendance
        workers_total = Worker.objects.filter(is_active=True).count()
        workers_present_today = Attendance.objects.filter(
            date=today, status__in=['present', 'half']
        ).count()
    except Exception:
        pass

    # Low stock materials
    low_stock_count = 0
    try:
        from apps.materials.models import Material
        low_stock_count = sum(
            1 for m in Material.objects.all()
            if m.is_low_stock or m.is_out_of_stock
        )
    except Exception:
        pass

    context = {
        'apt_stats': apt_counts,
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
        'chart_expenses': chart_expenses_list,
        'leads_new': leads_new,
        'leads_callback': leads_callback,
        'blocks': blocks,
        'workers_total': workers_total,
        'workers_present_today': workers_present_today,
        'low_stock_count': low_stock_count,
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
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    from datetime import date as dt
    month_start = dt(year, month, 1)
    if month == 12:
        month_end = dt(year + 1, 1, 1)
    else:
        month_end = dt(year, month + 1, 1)

    # Sales
    sales_qs = Sale.objects.filter(sale_date__gte=month_start, sale_date__lt=month_end)
    sales_count = sales_qs.count()
    sales_amount = sales_qs.aggregate(t=Sum('total_price'))['t'] or 0
    payments_amount = Payment.objects.filter(
        payment_date__gte=month_start, payment_date__lt=month_end
    ).aggregate(t=Sum('amount'))['t'] or 0

    # Expenses by category
    exp_by_cat = {}
    for exp in Expense.objects.filter(date__gte=month_start, date__lt=month_end):
        cat = exp.get_category_display()
        exp_by_cat[cat] = exp_by_cat.get(cat, 0) + float(exp.amount)
    total_expenses = sum(exp_by_cat.values())

    # Debts — single query
    debt_sales = Sale.objects.select_related('client', 'apartment__floor__block').annotate(
        debt=F('total_price') - F('paid_amount')
    ).filter(paid_amount__lt=F('total_price')).order_by('-total_price')[:20]

    # Available months for filter
    months_ru = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

    context = {
        'sales_count': sales_count,
        'sales_amount': sales_amount,
        'payments_amount': payments_amount,
        'exp_by_cat': exp_by_cat,
        'total_expenses': total_expenses,
        'profit': float(payments_amount) - total_expenses,
        'debt_sales': debt_sales,
        'year': year,
        'month': month,
        'month_name': months_ru[month],
        'months_ru': months_ru[1:],
        'today': today,
    }
    return render(request, 'reports/index.html', context)

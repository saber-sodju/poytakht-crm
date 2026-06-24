from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import Worker, Team, Position, Attendance, SalaryPayment
from apps.accounts.decorators import staff_required, finance_required


@login_required
@staff_required
def worker_list(request):
    q = request.GET.get('q', '')
    team_id = request.GET.get('team', '')
    active_only = request.GET.get('active', '1')

    workers = Worker.objects.select_related('position', 'team').all()

    if active_only != '0':
        workers = workers.filter(is_active=True)
    if q:
        workers = workers.filter(Q(full_name__icontains=q) | Q(phone__icontains=q))
    if team_id:
        workers = workers.filter(team_id=team_id)

    teams = Team.objects.all()
    total = workers.count()

    context = {
        'workers': workers,
        'teams': teams,
        'q': q,
        'team_id': team_id,
        'active_only': active_only,
        'total': total,
    }
    return render(request, 'workers/list.html', context)


@login_required
@staff_required
def worker_detail(request, pk):
    worker = get_object_or_404(Worker.objects.select_related('position', 'team', 'added_by'), pk=pk)
    today = date.today()
    month_start = today.replace(day=1)

    recent_attendance = worker.attendances.filter(date__gte=month_start).order_by('-date')
    salary_payments = worker.salary_payments.select_related('paid_by').order_by('-period_end')[:10]

    present_days = recent_attendance.filter(status='present').count()
    half_days = recent_attendance.filter(status='half').count()
    effective_days = present_days + half_days * Decimal('0.5')

    context = {
        'worker': worker,
        'recent_attendance': recent_attendance,
        'salary_payments': salary_payments,
        'present_days': present_days,
        'half_days': half_days,
        'effective_days': effective_days,
        'today': today,
        'month_start': month_start,
    }
    return render(request, 'workers/detail.html', context)


@login_required
@staff_required
def worker_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        position_id = request.POST.get('position') or None
        team_id = request.POST.get('team') or None
        salary_type = request.POST.get('salary_type', 'daily')
        salary_rate = request.POST.get('salary_rate', '0') or '0'
        hired_date = request.POST.get('hired_date') or date.today()
        passport_number = request.POST.get('passport_number', '')
        address = request.POST.get('address', '')
        note = request.POST.get('note', '')

        if not full_name:
            messages.error(request, 'ФИО обязательно.')
        else:
            Worker.objects.create(
                full_name=full_name, phone=phone,
                position_id=position_id, team_id=team_id,
                salary_type=salary_type, salary_rate=Decimal(salary_rate),
                hired_date=hired_date, passport_number=passport_number,
                address=address, note=note, added_by=request.user,
            )
            messages.success(request, f'Рабочий {full_name} добавлен.')
            return redirect('workers:list')

    positions = Position.objects.all()
    teams = Team.objects.all()
    return render(request, 'workers/form.html', {
        'positions': positions, 'teams': teams, 'title': 'Добавить рабочего'
    })


@login_required
@staff_required
def worker_edit(request, pk):
    worker = get_object_or_404(Worker, pk=pk)
    if request.method == 'POST':
        worker.full_name = request.POST.get('full_name', worker.full_name).strip()
        worker.phone = request.POST.get('phone', '')
        worker.position_id = request.POST.get('position') or None
        worker.team_id = request.POST.get('team') or None
        worker.salary_type = request.POST.get('salary_type', 'daily')
        worker.salary_rate = Decimal(request.POST.get('salary_rate', '0') or '0')
        hired = request.POST.get('hired_date')
        if hired:
            worker.hired_date = hired
        worker.passport_number = request.POST.get('passport_number', '')
        worker.address = request.POST.get('address', '')
        worker.note = request.POST.get('note', '')
        worker.is_active = request.POST.get('is_active') == 'on'
        if not worker.is_active and not worker.fired_date:
            worker.fired_date = date.today()
        worker.save()
        messages.success(request, 'Данные обновлены.')
        return redirect('workers:detail', pk=pk)

    positions = Position.objects.all()
    teams = Team.objects.all()
    return render(request, 'workers/form.html', {
        'worker': worker, 'positions': positions, 'teams': teams, 'title': 'Редактировать'
    })


@login_required
@staff_required
def attendance_day(request):
    today = date.today()
    selected_date = request.GET.get('date', str(today))
    try:
        from datetime import datetime
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        selected_date = today

    workers = Worker.objects.filter(is_active=True).select_related('position', 'team')
    existing = {a.worker_id: a for a in Attendance.objects.filter(date=selected_date)}

    if request.method == 'POST':
        for worker in workers:
            status = request.POST.get(f'status_{worker.pk}')
            note = request.POST.get(f'note_{worker.pk}', '')
            if status:
                att, created = Attendance.objects.get_or_create(
                    worker=worker, date=selected_date,
                    defaults={'status': status, 'note': note, 'recorded_by': request.user}
                )
                if not created:
                    att.status = status
                    att.note = note
                    att.save()
        messages.success(request, f'Посещаемость за {selected_date:%d.%m.%Y} сохранена.')
        return redirect('workers:attendance')

    rows = []
    for w in workers:
        rows.append({'worker': w, 'attendance': existing.get(w.pk)})

    context = {
        'rows': rows,
        'selected_date': selected_date,
        'today': today,
        'prev_date': selected_date - timedelta(days=1),
        'next_date': selected_date + timedelta(days=1),
        'status_choices': Attendance.STATUS_CHOICES,
    }
    return render(request, 'workers/attendance.html', context)


@login_required
@finance_required
def salary_list(request):
    payments = SalaryPayment.objects.select_related('worker', 'paid_by').order_by('-period_end')
    unpaid_total = payments.filter(is_paid=False).aggregate(t=Sum('total_amount'))['t'] or 0
    return render(request, 'workers/salary_list.html', {
        'payments': payments, 'unpaid_total': unpaid_total
    })


@login_required
@finance_required
def salary_create(request, worker_pk=None):
    workers = Worker.objects.filter(is_active=True).select_related('position')
    worker = get_object_or_404(Worker, pk=worker_pk) if worker_pk else None

    if request.method == 'POST':
        w_pk = request.POST.get('worker')
        w = get_object_or_404(Worker, pk=w_pk)
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        days_worked = int(request.POST.get('days_worked', 0) or 0)
        base_amount = Decimal(request.POST.get('base_amount', '0') or '0')
        bonus = Decimal(request.POST.get('bonus', '0') or '0')
        penalty = Decimal(request.POST.get('penalty', '0') or '0')
        note = request.POST.get('note', '')

        sp = SalaryPayment.objects.create(
            worker=w, period_start=period_start, period_end=period_end,
            days_worked=days_worked, base_amount=base_amount,
            bonus=bonus, penalty=penalty,
            total_amount=base_amount + bonus - penalty,
            note=note,
        )
        messages.success(request, f'Ведомость для {w.full_name} создана. Итого: ${sp.total_amount}')
        return redirect('workers:salary')

    today = date.today()
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    context = {
        'workers': workers,
        'selected_worker': worker,
        'period_start': month_start,
        'period_end': month_end,
    }
    return render(request, 'workers/salary_form.html', context)


@login_required
@finance_required
def salary_mark_paid(request, pk):
    sp = get_object_or_404(SalaryPayment, pk=pk)
    if request.method == 'POST':
        sp.is_paid = True
        sp.paid_date = date.today()
        sp.paid_by = request.user
        sp.save()
        messages.success(request, f'Зарплата для {sp.worker.full_name} отмечена как выплаченная.')
    return redirect('workers:salary')


@login_required
@staff_required
def team_list(request):
    teams = Team.objects.select_related('complex').prefetch_related('workers').all()
    return render(request, 'workers/teams.html', {'teams': teams})


@login_required
@staff_required
def team_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        complex_id = request.POST.get('complex') or None
        note = request.POST.get('note', '')
        if name:
            Team.objects.create(name=name, complex_id=complex_id, note=note)
            messages.success(request, f'Бригада «{name}» создана.')
            return redirect('workers:teams')
        messages.error(request, 'Введите название бригады.')

    from apps.complex.models import Complex
    complexes = Complex.objects.all()
    return render(request, 'workers/team_form.html', {'complexes': complexes})

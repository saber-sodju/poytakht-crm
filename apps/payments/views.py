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
@staff_required
def payment_receipt(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related(
            'sale__client', 'sale__apartment__floor__block__complex', 'added_by'
        ), pk=pk
    )
    rows = [
        ('Клиент', payment.sale.client.full_name),
        ('Телефон', payment.sale.client.phone),
        ('Квартира', str(payment.sale.apartment)),
        ('Комплекс', payment.sale.apartment.floor.block.complex.name),
        ('Договор №', payment.sale.contract_number or '—'),
        ('Принял', payment.added_by.display_name if payment.added_by else '—'),
    ]
    return render(request, 'payments/receipt.html', {'payment': payment, 'rows': rows})


@login_required
@staff_required
def payment_receipt_pdf(request, pk):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from django.http import HttpResponse

    payment = get_object_or_404(
        Payment.objects.select_related(
            'sale__client', 'sale__apartment__floor__block__complex', 'added_by'
        ), pk=pk
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('title', parent=styles['Heading1'],
                                 fontSize=18, spaceAfter=6, alignment=1)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'],
                               fontSize=11, textColor=colors.grey, alignment=1)
    normal = styles['Normal']
    normal.fontSize = 11

    elements.append(Paragraph('КВИТАНЦИЯ ОБ ОПЛАТЕ', title_style))
    elements.append(Paragraph('Poyakht Insoot / Поытахт Иншоот', sub_style))
    elements.append(Spacer(1, 0.5*cm))

    data = [
        ['Квитанция №', f'PMT-{payment.pk:04d}'],
        ['Дата оплаты', payment.payment_date.strftime('%d.%m.%Y')],
        ['Клиент', payment.sale.client.full_name],
        ['Телефон', payment.sale.client.phone],
        ['Квартира', str(payment.sale.apartment)],
        ['Комплекс', payment.sale.apartment.floor.block.complex.name],
        ['Договор №', payment.sale.contract_number or '—'],
        ['Сумма оплаты', f'${payment.amount:,.2f}'],
        ['Всего оплачено', f'${payment.sale.paid_amount:,.2f}'],
        ['Остаток долга', f'${payment.sale.remaining_amount:,.2f}'],
        ['Принял', payment.added_by.display_name if payment.added_by else '—'],
    ]

    table = Table(data, colWidths=[7*cm, 10*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f0e7')),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d4b06a')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#d4af37')),
        ('FONTNAME', (0, 7), (-1, 7), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 7), (-1, 7), 13),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#fffaf2')]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1*cm))

    if payment.note:
        elements.append(Paragraph(f'Примечание: {payment.note}', normal))
        elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph('Подпись: _________________', normal))

    doc.build(elements)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="receipt-{payment.pk}.pdf"'
    return response


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

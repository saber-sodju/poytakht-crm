from django import forms
from django.db.models import F

from .models import Payment, PaymentSchedule


def _sale_label(sale):
    """«Иванов И. — кв. 101 (Блок А), долг $7 000»"""
    return (
        f'{sale.client.full_name} — {sale.apartment.unit_label.lower()} '
        f'{sale.apartment.number} ({sale.apartment.block.name}), '
        f'долг ${sale.remaining_amount:,.0f}'.replace(',', ' ')
    )


class SalePickerForm(forms.Form):
    """Step one when no sale is given: choose which apartment's account to pay
    into. A client can own several apartments, and each has its own debt and
    its own schedule — they must never be worked on together."""

    sale = forms.ModelChoiceField(
        label='По какой квартире платёж',
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='— выберите клиента и квартиру —',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.sales.models import Sale
        qs = (
            Sale.objects
            .filter(is_cancelled=False, paid_amount__lt=F('total_price'))
            .select_related('client', 'apartment__floor__block')
            .order_by('client__full_name', 'apartment__number')
        )
        self.fields['sale'].queryset = qs
        self.fields['sale'].label_from_instance = _sale_label


class PaymentForm(forms.ModelForm):
    """Always bound to ONE sale. The sale is fixed by the view, and the
    schedule dropdown only ever offers that sale's own unpaid instalments —
    previously it listed every schedule row in the database, so a payment on
    one apartment could mark another apartment's instalment as paid."""

    class Meta:
        model = Payment
        fields = ['sale', 'schedule', 'amount', 'payment_date', 'receipt', 'note']
        widgets = {
            'sale': forms.HiddenInput(),
            'schedule': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, sale=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sale = sale
        if sale is not None:
            from apps.sales.models import Sale
            self.fields['sale'].queryset = Sale.objects.filter(pk=sale.pk)
            self.fields['sale'].initial = sale
            self.fields['schedule'].queryset = (
                sale.schedule.filter(is_paid=False).order_by('due_date')
            )
            self.fields['schedule'].label = 'Платёж по графику'
            self.fields['schedule'].empty_label = '— вне графика (разовый платёж) —'
            self.fields['schedule'].label_from_instance = (
                lambda s: f'{s.due_date:%d.%m.%Y} — ${s.amount:,.2f}'.replace(',', ' ')
            )
            self.fields['receipt'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned = super().clean()
        sale = cleaned.get('sale')
        schedule = cleaned.get('schedule')
        # Defence in depth: even with a hand-crafted POST, a payment can only
        # ever settle an instalment belonging to its own sale.
        if sale and schedule and schedule.sale_id != sale.pk:
            self.add_error('schedule', 'Этот платёж относится к другой квартире.')
        return cleaned


class ScheduleForm(forms.ModelForm):
    """Adding a schedule row: the sale is fixed by the view, not picked from a
    list of every sale in the system."""

    class Meta:
        model = PaymentSchedule
        fields = ['sale', 'due_date', 'amount', 'note']
        widgets = {
            'sale': forms.HiddenInput(),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, sale=None, **kwargs):
        super().__init__(*args, **kwargs)
        if sale is not None:
            from apps.sales.models import Sale
            self.fields['sale'].queryset = Sale.objects.filter(pk=sale.pk)
            self.fields['sale'].initial = sale

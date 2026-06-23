from django import forms
from .models import Payment, PaymentSchedule


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['sale', 'schedule', 'amount', 'payment_date', 'receipt', 'note']
        widgets = {
            'sale': forms.Select(attrs={'class': 'form-select'}),
            'schedule': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = PaymentSchedule
        fields = ['sale', 'due_date', 'amount', 'note']
        widgets = {
            'sale': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

from django import forms
from django.utils import timezone
from .models import Booking, Sale


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['apartment', 'client', 'start_date', 'end_date', 'deposit', 'note']
        widgets = {
            'apartment': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'deposit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.complex.models import Apartment
        self.fields['apartment'].queryset = Apartment.objects.filter(status='free').select_related('floor__block')


class SaleForm(forms.ModelForm):
    initial_payment = forms.DecimalField(
        label='Первый платёж / Аванс ($)',
        required=False,
        min_value=0,
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'
        }),
        help_text='Если клиент внёс деньги сразу — укажите сумму, платёж создастся автоматически.',
    )

    class Meta:
        model = Sale
        fields = ['apartment', 'client', 'total_price', 'payment_type',
                  'contract_number', 'contract_date', 'sale_date', 'note']
        widgets = {
            'apartment': forms.Select(attrs={'class': 'form-select'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sale_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.complex.models import Apartment
        self.fields['apartment'].queryset = Apartment.objects.filter(
            status__in=['free', 'booked']
        ).select_related('floor__block')

    def clean(self):
        cleaned = super().clean()
        initial_payment = cleaned.get('initial_payment')
        total_price = cleaned.get('total_price')
        if initial_payment and total_price and initial_payment > total_price:
            self.add_error(
                'initial_payment',
                'Первый платёж не может быть больше цены продажи.'
            )
        return cleaned

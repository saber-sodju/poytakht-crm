from django import forms
from .models import Expense, CATEGORY_CHOICES


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['complex', 'block', 'category', 'amount', 'date', 'description', 'document']
        widgets = {
            'complex': forms.Select(attrs={'class': 'form-select'}),
            'block': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

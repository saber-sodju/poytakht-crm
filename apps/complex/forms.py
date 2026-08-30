from django import forms
from .models import Complex, Block, Floor, Apartment, ConstructionStage, PhotoReport


class ComplexForm(forms.ModelForm):
    class Meta:
        model = Complex
        fields = ['name', 'address', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BlockForm(forms.ModelForm):
    class Meta:
        model = Block
        fields = ['complex', 'name', 'budget_planned', 'description']
        widgets = {
            'complex': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'budget_planned': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FloorForm(forms.ModelForm):
    class Meta:
        model = Floor
        fields = ['block', 'number']
        widgets = {
            'block': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ApartmentForm(forms.ModelForm):
    class Meta:
        model = Apartment
        fields = ['floor', 'number', 'apartment_type', 'area', 'price_per_sqm',
                  'total_price', 'status', 'layout_image', 'description']
        widgets = {
            'floor': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.TextInput(attrs={'class': 'form-control'}),
            'apartment_type': forms.Select(attrs={'class': 'form-select'}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_per_sqm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BulkApartmentForm(forms.Form):
    floor_from = forms.IntegerField(
        label='Этаж с', min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    floor_to = forms.IntegerField(
        label='Этаж по', min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    apartments_per_floor = forms.IntegerField(
        label='Квартир на этаже', min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    apartment_type = forms.ChoiceField(
        label='Тип', choices=Apartment.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    area = forms.DecimalField(
        label='Площадь (м²)', min_value=0, max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )
    price_per_sqm = forms.DecimalField(
        label='Цена за м² ($)', min_value=0, max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    )

    def clean(self):
        cleaned = super().clean()
        floor_from = cleaned.get('floor_from')
        floor_to = cleaned.get('floor_to')
        if floor_from is not None and floor_to is not None and floor_to < floor_from:
            self.add_error('floor_to', 'Этаж "по" не может быть меньше этажа "с".')
        return cleaned


class ConstructionStageForm(forms.ModelForm):
    class Meta:
        model = ConstructionStage
        fields = ['stage', 'status', 'progress', 'responsible', 'start_date', 'end_date', 'note']
        widgets = {
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'progress': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'responsible': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PhotoReportForm(forms.ModelForm):
    class Meta:
        model = PhotoReport
        fields = ['block', 'stage', 'photo', 'caption']
        widgets = {
            'block': forms.Select(attrs={'class': 'form-select'}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
        }

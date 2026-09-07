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
    # Optional: create the block's empty floors in one go, so the manager
    # doesn't click "+ Этаж" twelve times. Apartments are deliberately NOT
    # generated here — a real floor is a mix (two 1-room, one 2-room, one
    # 3-room...), never N identical flats, so they're laid out per floor and
    # then copied floor-to-floor (see FloorLayoutCopyForm).
    floors_count = forms.IntegerField(
        label='Сколько этажей создать сразу', required=False, min_value=1, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'необязательно'}),
    )

    class Meta:
        model = Block
        fields = ['complex', 'name', 'budget_planned', 'description']
        widgets = {
            'complex': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'budget_planned': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FloorLayoutCopyForm(forms.Form):
    """Copy one floor's apartment composition onto a range of other floors."""

    floor_from = forms.IntegerField(
        label='Скопировать на этажи с', min_value=1, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    floor_to = forms.IntegerField(
        label='по', min_value=1, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    price_step_per_floor = forms.DecimalField(
        label='Надбавка к цене за м² на каждый этаж выше ($)',
        required=False, max_digits=12, decimal_places=2, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        help_text='0 — цена одинаковая на всех этажах.',
    )

    def clean(self):
        cleaned = super().clean()
        floor_from = cleaned.get('floor_from')
        floor_to = cleaned.get('floor_to')
        if floor_from is not None and floor_to is not None and floor_to < floor_from:
            self.add_error('floor_to', 'Конечный этаж не может быть меньше начального.')
        if cleaned.get('price_step_per_floor') is None:
            cleaned['price_step_per_floor'] = 0
        return cleaned


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

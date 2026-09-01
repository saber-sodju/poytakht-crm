from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm, SetPasswordForm
from .models import CustomUser

# Roles a "Главный администратор" (not a director) is allowed to create/edit.
ADMIN_MANAGEABLE_ROLES = [CustomUser.ROLE_MANAGER, CustomUser.ROLE_ACCOUNTANT]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя', 'autofocus': True})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'})
    )
    remember_me = forms.BooleanField(
        label='Запомнить меня', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class UserCreateForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        if actor is not None and actor.is_admin:
            self.fields['role'].choices = [
                c for c in CustomUser.ROLE_CHOICES if c[0] in ADMIN_MANAGEABLE_ROLES
            ]


class UserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active', 'avatar']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor is not None and actor.is_admin:
            self.fields['role'].choices = [
                c for c in CustomUser.ROLE_CHOICES if c[0] in ADMIN_MANAGEABLE_ROLES
            ]


class StyledPasswordChangeForm(PasswordChangeForm):
    """Self-service password change — same Bootstrap styling as the rest of the app."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class StyledSetPasswordForm(SetPasswordForm):
    """Director/admin setting a new password for a managed user."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

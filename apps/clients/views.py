from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
import random
import string

from .models import Client, Lead
from .forms import ClientForm, LeadForm
from apps.accounts.decorators import staff_required


@login_required
@staff_required
def client_list(request):
    q = request.GET.get('q', '')
    clients = Client.objects.prefetch_related('sales').all()
    if q:
        clients = clients.filter(
            Q(full_name__icontains=q) | Q(phone__icontains=q) |
            Q(passport_number__icontains=q) | Q(email__icontains=q)
        )
    return render(request, 'clients/list.html', {'clients': clients, 'q': q})


@login_required
@staff_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.added_by = request.user
        client.save()
        messages.success(request, f'Клиент {client.full_name} добавлен.')
        return redirect('clients:client_detail', pk=client.pk)
    return render(request, 'clients/form.html', {'form': form, 'title': 'Новый клиент'})


@login_required
@staff_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = client.sales.prefetch_related('payments', 'schedule').all()
    documents = client.documents.all() if hasattr(client, 'documents') else []
    return render(request, 'clients/detail.html', {
        'client': client, 'sales': sales, 'documents': documents
    })


@login_required
@staff_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Данные клиента обновлены.')
        return redirect('clients:client_detail', pk=pk)
    return render(request, 'clients/form.html', {'form': form, 'title': f'Редактировать: {client.full_name}', 'object': client})


@login_required
@staff_required
def client_create_account(request, pk):
    from apps.accounts.models import CustomUser
    client = get_object_or_404(Client, pk=pk)

    if client.user:
        messages.warning(request, f'У клиента уже есть аккаунт: {client.user.username}')
        return redirect('clients:client_detail', pk=pk)

    # Generate username from phone number (digits only)
    base_username = 'client_' + ''.join(filter(str.isdigit, client.phone))[-8:]
    username = base_username
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f'{base_username}_{counter}'
        counter += 1

    # Generate random password
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

    user = CustomUser.objects.create_user(
        username=username,
        password=password,
        first_name=client.full_name.split()[0] if client.full_name else '',
        last_name=' '.join(client.full_name.split()[1:]) if len(client.full_name.split()) > 1 else '',
        role='client',
        phone=client.phone,
        email=client.email or '',
    )
    client.user = user
    client.save()

    messages.success(
        request,
        f'Аккаунт создан! Логин: {username} | Пароль: {password} — сохраните и передайте клиенту.'
    )
    return redirect('clients:client_detail', pk=pk)


@login_required
@staff_required
def lead_list(request):
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    today = timezone.now().date()

    leads = Lead.objects.select_related('assigned_to').all()
    if q:
        leads = leads.filter(Q(name__icontains=q) | Q(phone__icontains=q))
    if status_filter:
        leads = leads.filter(status=status_filter)

    due_today = Lead.objects.filter(next_contact_date=today).exclude(status__in=['bought', 'refused']).count()
    return render(request, 'clients/leads.html', {
        'leads': leads,
        'q': q,
        'status_filter': status_filter,
        'status_choices': Lead.STATUS_CHOICES,
        'due_today': due_today,
    })


@login_required
@staff_required
def lead_create(request):
    form = LeadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        lead = form.save()
        messages.success(request, f'Лид {lead.name} добавлен.')
        return redirect('clients:leads')
    return render(request, 'clients/lead_form.html', {'form': form, 'title': 'Новый лид'})


@login_required
@staff_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    form = LeadForm(request.POST or None, instance=lead)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Лид обновлён.')
        return redirect('clients:leads')
    return render(request, 'clients/lead_form.html', {'form': form, 'title': f'Лид: {lead.name}', 'object': lead})

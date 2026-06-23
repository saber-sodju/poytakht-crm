from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone

from .models import Expense, CATEGORY_CHOICES
from .forms import ExpenseForm
from apps.complex.models import Block
from apps.accounts.decorators import finance_required, staff_required


@login_required
@staff_required
def expense_list(request):
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')
    block_id = request.GET.get('block', '')

    expenses = Expense.objects.select_related('complex', 'block', 'added_by').all()

    if q:
        expenses = expenses.filter(description__icontains=q)
    if category:
        expenses = expenses.filter(category=category)
    if block_id:
        expenses = expenses.filter(block_id=block_id)

    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    by_category = []
    for cat_key, cat_name in CATEGORY_CHOICES:
        cat_total = expenses.filter(category=cat_key).aggregate(t=Sum('amount'))['t'] or 0
        if cat_total > 0:
            by_category.append({'key': cat_key, 'name': cat_name, 'total': cat_total})

    blocks = Block.objects.select_related('complex').all()

    return render(request, 'expenses/list.html', {
        'expenses': expenses,
        'q': q,
        'category': category,
        'block_id': block_id,
        'total': total,
        'by_category': by_category,
        'categories': CATEGORY_CHOICES,
        'blocks': blocks,
    })


@login_required
@finance_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        expense = form.save(commit=False)
        expense.added_by = request.user
        expense.save()
        block = expense.block
        if block and block.is_over_budget:
            messages.warning(request, f'⚠️ Бюджет блока «{block.name}» превышен!')
        messages.success(request, f'Расход ${expense.amount} добавлен.')
        return redirect('expenses:list')
    return render(request, 'expenses/form.html', {'form': form, 'title': 'Новый расход'})


@login_required
@finance_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Расход обновлён.')
        return redirect('expenses:list')
    return render(request, 'expenses/form.html', {'form': form, 'title': 'Редактировать расход', 'object': expense})


@login_required
@finance_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Расход удалён.')
        return redirect('expenses:list')
    return render(request, 'expenses/confirm_delete.html', {'expense': expense})

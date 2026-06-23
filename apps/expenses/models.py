from django.db import models


CATEGORY_CHOICES = [
    ('materials', 'Материалы'),
    ('salary', 'Зарплата'),
    ('equipment', 'Техника'),
    ('transport', 'Транспорт'),
    ('documents', 'Документы'),
    ('taxes', 'Налоги'),
    ('utilities', 'Коммунальные'),
    ('other', 'Прочее'),
]

CATEGORY_ICONS = {
    'materials': '🧱',
    'salary': '👷',
    'equipment': '🏗️',
    'transport': '🚛',
    'documents': '📄',
    'taxes': '🏦',
    'utilities': '⚡',
    'other': '📦',
}


class Expense(models.Model):
    complex = models.ForeignKey(
        'complex.Complex', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='expenses', verbose_name='Комплекс'
    )
    block = models.ForeignKey(
        'complex.Block', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='expenses', verbose_name='Блок'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='Категория')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма ($)')
    date = models.DateField(verbose_name='Дата')
    description = models.TextField(blank=True, verbose_name='Описание')
    document = models.FileField(upload_to='expense_docs/', blank=True, null=True, verbose_name='Документ/Чек')
    added_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        verbose_name='Добавил'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_category_display()} — ${self.amount} — {self.date}'

    @property
    def category_icon(self):
        return CATEGORY_ICONS.get(self.category, '📦')

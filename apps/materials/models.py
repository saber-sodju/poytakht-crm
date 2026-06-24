from django.db import models


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name='Поставщик', db_index=True)
    phone = models.CharField(max_length=25, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес')
    contact_person = models.CharField(max_length=200, blank=True, verbose_name='Контактное лицо')
    note = models.TextField(blank=True, verbose_name='Примечание')
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class Material(models.Model):
    UNIT_CHOICES = [
        ('kg', 'кг'),
        ('ton', 'тонна'),
        ('m', 'м'),
        ('m2', 'м²'),
        ('m3', 'м³'),
        ('piece', 'шт'),
        ('bag', 'мешок'),
        ('roll', 'рулон'),
        ('liter', 'литр'),
        ('box', 'коробка'),
    ]

    name = models.CharField(max_length=200, verbose_name='Название', db_index=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, verbose_name='Ед. изм.')
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='На складе'
    )
    min_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Мин. запас (предупреждение)'
    )
    price_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='Цена за ед. ($)'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='materials', verbose_name='Осн. поставщик'
    )
    note = models.TextField(blank=True, verbose_name='Примечание')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_unit_display()})'

    @property
    def total_value(self):
        return self.quantity * self.price_per_unit

    @property
    def is_low_stock(self):
        return self.min_quantity > 0 and self.quantity <= self.min_quantity

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def status_color(self):
        if self.is_out_of_stock:
            return 'danger'
        if self.is_low_stock:
            return 'warning'
        return 'success'

    @property
    def status_label(self):
        if self.is_out_of_stock:
            return 'Нет на складе'
        if self.is_low_stock:
            return 'Мало'
        return 'В наличии'


class MaterialMovement(models.Model):
    DIRECTION_IN = 'in'
    DIRECTION_OUT = 'out'
    DIRECTION_CHOICES = [
        (DIRECTION_IN, 'Приход'),
        (DIRECTION_OUT, 'Расход'),
    ]

    material = models.ForeignKey(
        Material, on_delete=models.CASCADE,
        related_name='movements', verbose_name='Материал'
    )
    direction = models.CharField(
        max_length=5, choices=DIRECTION_CHOICES, verbose_name='Тип', db_index=True
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Количество')
    price_per_unit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name='Цена за ед. ($)'
    )
    total_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name='Сумма ($)'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movements', verbose_name='Поставщик'
    )
    block = models.ForeignKey(
        'complex.Block', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='material_movements', verbose_name='Блок/Объект'
    )
    date = models.DateField(verbose_name='Дата', db_index=True)
    note = models.TextField(blank=True, verbose_name='Примечание')
    added_by = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.SET_NULL, null=True,
        verbose_name='Добавил'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Движение материала'
        verbose_name_plural = 'Движения материалов'
        ordering = ['-date', '-created_at']

    def __str__(self):
        label = 'Приход' if self.direction == self.DIRECTION_IN else 'Расход'
        return f'{label}: {self.material.name} × {self.quantity}'

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.price_per_unit
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            mat = self.material
            if self.direction == self.DIRECTION_IN:
                mat.quantity += self.quantity
                if self.price_per_unit > 0:
                    mat.price_per_unit = self.price_per_unit
            else:
                from decimal import Decimal
                mat.quantity = max(Decimal('0'), mat.quantity - self.quantity)
            mat.save(update_fields=['quantity', 'price_per_unit', 'updated_at'])

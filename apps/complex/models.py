from django.db import models
from django.utils import timezone


class Complex(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    address = models.TextField(verbose_name='Адрес')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Жилой комплекс'
        verbose_name_plural = 'Жилые комплексы'

    def __str__(self):
        return self.name

    @property
    def total_apartments(self):
        return Apartment.objects.filter(floor__block__complex=self).count()

    @property
    def free_apartments(self):
        return Apartment.objects.filter(floor__block__complex=self, status='free').count()

    @property
    def sold_apartments(self):
        return Apartment.objects.filter(floor__block__complex=self, status='sold').count()


class Block(models.Model):
    complex = models.ForeignKey(Complex, on_delete=models.CASCADE, related_name='blocks', verbose_name='Комплекс')
    name = models.CharField(max_length=100, verbose_name='Название блока')
    budget_planned = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Плановый бюджет ($)')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Блок'
        verbose_name_plural = 'Блоки'
        ordering = ['name']

    def __str__(self):
        return f'{self.complex.name} — {self.name}'

    @property
    def floors_count(self):
        return self.floors.count()

    @property
    def total_apartments(self):
        return Apartment.objects.filter(floor__block=self).count()

    @property
    def free_apartments(self):
        return Apartment.objects.filter(floor__block=self, status='free').count()

    @property
    def sold_apartments(self):
        return Apartment.objects.filter(floor__block=self, status='sold').count()

    @property
    def budget_actual(self):
        return self.expenses.aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def budget_remaining(self):
        return self.budget_planned - self.budget_actual

    @property
    def is_over_budget(self):
        return self.budget_actual > self.budget_planned and self.budget_planned > 0


class Floor(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='floors', verbose_name='Блок')
    number = models.IntegerField(verbose_name='Номер этажа')

    class Meta:
        verbose_name = 'Этаж'
        verbose_name_plural = 'Этажи'
        ordering = ['number']
        unique_together = ['block', 'number']

    def __str__(self):
        return f'{self.block.name}, этаж {self.number}'


class Apartment(models.Model):
    STATUS_FREE = 'free'
    STATUS_BOOKED = 'booked'
    STATUS_SOLD = 'sold'
    STATUS_UNAVAILABLE = 'unavailable'

    STATUS_CHOICES = [
        (STATUS_FREE, 'Свободна'),
        (STATUS_BOOKED, 'Забронирована'),
        (STATUS_SOLD, 'Продана'),
        (STATUS_UNAVAILABLE, 'Недоступна'),
    ]

    TYPE_CHOICES = [
        ('1', '1-комнатная'),
        ('2', '2-комнатная'),
        ('3', '3-комнатная'),
        ('4', '4-комнатная'),
        ('studio', 'Студия'),
        ('penthouse', 'Пентхаус'),
    ]

    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='apartments', verbose_name='Этаж')
    number = models.CharField(max_length=20, verbose_name='Номер квартиры')
    apartment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Тип')
    area = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='Площадь (м²)')
    price_per_sqm = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Цена за м² ($)')
    total_price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Общая цена ($)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_FREE, verbose_name='Статус')
    layout_image = models.ImageField(upload_to='layouts/', blank=True, null=True, verbose_name='Планировка')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Квартира'
        verbose_name_plural = 'Квартиры'
        ordering = ['floor__number', 'number']

    def __str__(self):
        return f'Кв. {self.number} ({self.floor})'

    @property
    def block(self):
        return self.floor.block

    @property
    def status_color(self):
        return {
            'free': 'success',
            'booked': 'warning',
            'sold': 'danger',
            'unavailable': 'secondary',
        }.get(self.status, 'secondary')

    @property
    def active_sale(self):
        return self.sale if hasattr(self, 'sale') else None

    @property
    def active_booking(self):
        return self.booking if hasattr(self, 'booking') else None


class ConstructionStage(models.Model):
    STAGE_CHOICES = [
        ('foundation', 'Фундамент'),
        ('frame', 'Каркас'),
        ('walls', 'Стены'),
        ('roof', 'Крыша'),
        ('windows', 'Окна'),
        ('facade', 'Фасад'),
        ('utilities', 'Коммуникации'),
        ('interior', 'Внутренняя отделка'),
        ('completed', 'Завершено'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('paused', 'Приостановлено'),
    ]

    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='stages', verbose_name='Блок')
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES, verbose_name='Этап')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    progress = models.IntegerField(default=0, verbose_name='Прогресс (%)')
    responsible = models.CharField(max_length=200, blank=True, verbose_name='Ответственный')
    start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    note = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Этап строительства'
        verbose_name_plural = 'Этапы строительства'
        unique_together = ['block', 'stage']

    def __str__(self):
        return f'{self.block.name} — {self.get_stage_display()}'


class PhotoReport(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='photos', verbose_name='Блок')
    stage = models.ForeignKey(ConstructionStage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Этап')
    photo = models.ImageField(upload_to='construction/', verbose_name='Фото')
    caption = models.CharField(max_length=300, blank=True, verbose_name='Подпись')
    uploaded_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name='Загрузил')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Фотоотчёт'
        verbose_name_plural = 'Фотоотчёты'
        ordering = ['-created_at']

    def __str__(self):
        return f'Фото: {self.block.name} {self.created_at.date()}'

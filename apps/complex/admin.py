from django.contrib import admin
from .models import Complex, Block, Floor, Apartment, ConstructionStage, PhotoReport


@admin.register(Complex)
class ComplexAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at']


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['name', 'complex', 'budget_planned', 'created_at']
    list_filter = ['complex']


class ApartmentInline(admin.TabularInline):
    model = Apartment
    extra = 0


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['block', 'number']
    inlines = [ApartmentInline]


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ['number', 'floor', 'apartment_type', 'area', 'total_price', 'status']
    list_filter = ['status', 'apartment_type', 'floor__block']
    search_fields = ['number']


@admin.register(ConstructionStage)
class StageAdmin(admin.ModelAdmin):
    list_display = ['block', 'stage', 'status', 'progress']


@admin.register(PhotoReport)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['block', 'stage', 'uploaded_by', 'created_at']

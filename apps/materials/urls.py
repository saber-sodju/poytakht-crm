from django.urls import path
from . import views

app_name = 'materials'

urlpatterns = [
    path('', views.material_list, name='list'),
    path('create/', views.material_create, name='create'),
    path('<int:pk>/', views.material_detail, name='detail'),
    path('<int:pk>/edit/', views.material_edit, name='edit'),
    path('movement/', views.movement_create, name='movement'),
    path('movement/<int:material_pk>/', views.movement_create, name='movement_for'),
    path('suppliers/', views.supplier_list, name='suppliers'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
]

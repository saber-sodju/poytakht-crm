from django.urls import path
from . import views

app_name = 'complex'

urlpatterns = [
    path('', views.complex_list, name='list'),
    path('create/', views.complex_create, name='create'),
    path('<int:pk>/', views.complex_detail, name='complex_detail'),
    path('blocks/create/', views.block_create, name='block_create'),
    path('blocks/<int:pk>/', views.block_detail, name='block_detail'),
    path('blocks/<int:block_pk>/floors/add/', views.floor_create, name='floor_create'),
    path('blocks/<int:block_pk>/stages/update/', views.stage_update, name='stage_update'),
    path('blocks/<int:block_pk>/photos/add/', views.photo_add, name='photo_add'),
    path('apartments/create/', views.apartment_create, name='apartment_create'),
    path('apartments/create/floor/<int:floor_pk>/', views.apartment_create, name='apartment_create_floor'),
    path('apartments/<int:pk>/', views.apartment_detail, name='apartment_detail'),
    path('apartments/<int:pk>/edit/', views.apartment_edit, name='apartment_edit'),
    path('apartments/<int:pk>/api/', views.apartment_api, name='apartment_api'),
]

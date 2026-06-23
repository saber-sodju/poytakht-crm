from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='list'),
    path('create/', views.sale_create, name='create'),
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('bookings/', views.booking_list, name='bookings'),
    path('bookings/create/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
]

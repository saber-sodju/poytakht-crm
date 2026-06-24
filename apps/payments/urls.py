from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='list'),
    path('add/', views.payment_add, name='add'),
    path('overdue/', views.overdue_list, name='overdue'),
    path('upcoming/', views.upcoming_list, name='upcoming'),
    path('schedule/<int:sale_pk>/add/', views.schedule_add, name='schedule_add'),
    path('<int:pk>/receipt/', views.payment_receipt, name='receipt'),
    path('<int:pk>/receipt/pdf/', views.payment_receipt_pdf, name='receipt_pdf'),
]

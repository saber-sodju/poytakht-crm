from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('reports/', views.reports_view, name='reports'),
]

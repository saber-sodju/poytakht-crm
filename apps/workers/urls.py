from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('', views.worker_list, name='list'),
    path('create/', views.worker_create, name='create'),
    path('<int:pk>/', views.worker_detail, name='detail'),
    path('<int:pk>/edit/', views.worker_edit, name='edit'),
    path('attendance/', views.attendance_day, name='attendance'),
    path('teams/', views.team_list, name='teams'),
    path('teams/create/', views.team_create, name='team_create'),
    path('salary/', views.salary_list, name='salary'),
    path('salary/create/', views.salary_create, name='salary_create'),
    path('salary/create/<int:worker_pk>/', views.salary_create, name='salary_create_for'),
    path('salary/<int:pk>/paid/', views.salary_mark_paid, name='salary_paid'),
]

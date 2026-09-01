from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.users_list, name='users'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/deactivate/', views.user_deactivate, name='user_deactivate'),
    path('users/<int:pk>/activate/', views.user_activate, name='user_activate'),
    path('users/<int:pk>/set-password/', views.user_set_password, name='user_set_password'),
    path('profile/password/', views.password_change, name='password_change'),
    path('notifications/read/', views.mark_notifications_read, name='notifications_read'),
    path('profile/', views.profile_view, name='profile'),
]

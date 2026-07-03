from django.contrib import admin
from django.urls import path, include
from . import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', core_views.service_worker, name='service_worker'),
    path('manifest.json', core_views.pwa_manifest, name='pwa_manifest'),
    # Apple looks for this at the root automatically (fallback discovery)
    path('apple-touch-icon.png', core_views.apple_touch_icon),
    path('apple-touch-icon-precomposed.png', core_views.apple_touch_icon),
    # Media served with login + object-level access control (works in prod too,
    # where the old static() helper returned nothing with DEBUG=False)
    path('media/<path:path>', core_views.protected_media, name='protected_media'),
    path('', include('apps.dashboard.urls')),
    path('auth/', include('apps.accounts.urls')),
    path('complex/', include('apps.complex.urls')),
    path('clients/', include('apps.clients.urls')),
    path('sales/', include('apps.sales.urls')),
    path('payments/', include('apps.payments.urls')),
    path('expenses/', include('apps.expenses.urls')),
    path('audit/', include('apps.audit.urls')),
    path('workers/', include('apps.workers.urls')),
    path('materials/', include('apps.materials.urls')),
]

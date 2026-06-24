from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', core_views.service_worker, name='service_worker'),
    path('manifest.json', core_views.pwa_manifest, name='pwa_manifest'),
    # Apple looks for this at the root automatically (fallback discovery)
    path('apple-touch-icon.png', core_views.apple_touch_icon),
    path('apple-touch-icon-precomposed.png', core_views.apple_touch_icon),
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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

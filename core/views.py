from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def service_worker(request):
    """Serve the service worker JS as a Django template so {% static %} tags resolve correctly."""
    response = render(request, 'pwa/sw.js', content_type='application/javascript; charset=utf-8')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


@never_cache
def pwa_manifest(request):
    """Serve manifest.json with correct headers."""
    import json, os
    from django.conf import settings
    from django.http import JsonResponse

    manifest_path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'pwa', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        # Fallback: read from STATICFILES_DIRS
        for d in settings.STATICFILES_DIRS:
            p = os.path.join(d, 'pwa', 'manifest.json')
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
        else:
            data = {}

    return JsonResponse(data, content_type='application/manifest+json')

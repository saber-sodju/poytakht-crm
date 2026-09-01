import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.templatetags.static import static as static_url


def _can_access_media(user, path) -> bool:
    """Staff: full access. Client role: only receipts on their own payments."""
    if not user.is_client_role:
        return True
    if path.startswith('receipts/') and hasattr(user, 'client_profile'):
        from apps.payments.models import Payment
        return Payment.objects.filter(receipt=path, sale__client=user.client_profile).exists()
    return False


@login_required
def protected_media(request, path):
    """
    Serve /media/ files with access control.

    - Staff members: full access.
    - Client role: only receipts belonging to their own payments.
    - Path traversal blocked via resolved-path check (local-disk mode).

    When USE_S3_MEDIA is on, files live in the S3-compatible bucket instead
    of local disk — access is checked the same way, then the browser is
    redirected to a short-lived signed URL instead of streaming the file
    through Django.
    """
    if not _can_access_media(request.user, path):
        raise Http404   # 404, not 403 — don't reveal that the file exists

    if getattr(settings, 'USE_S3_MEDIA', False):
        import boto3
        from botocore.exceptions import ClientError
        s3 = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        try:
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': path},
                ExpiresIn=60,   # link only needs to survive the redirect
            )
        except ClientError:
            raise Http404
        return redirect(url)

    media_root = Path(settings.MEDIA_ROOT).resolve()
    full_path = (media_root / path).resolve()

    # Block ../../ traversal — resolved path must stay inside MEDIA_ROOT
    if media_root not in full_path.parents:
        raise Http404
    if not full_path.is_file():
        raise Http404

    return FileResponse(open(full_path, 'rb'))


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
    import json
    from django.conf import settings
    from django.http import JsonResponse

    manifest_path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'pwa', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        for d in settings.STATICFILES_DIRS:
            p = os.path.join(d, 'pwa', 'manifest.json')
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                break
        else:
            data = {}

    return JsonResponse(data, content_type='application/manifest+json')


def apple_touch_icon(request):
    """
    Serve apple-touch-icon.png from the root path /apple-touch-icon.png.
    Safari automatically looks for it here when no <link> is found or as a fallback.
    """
    return redirect(static_url('pwa/icons/apple-touch-icon.png'), permanent=False)

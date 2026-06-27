import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _env(key, default=None):
    return os.getenv(key, default)


# ── Core ──────────────────────────────────────────────────────────────────────
DEBUG = _env('DEBUG', 'False') == 'True'

SECRET_KEY = _env('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Dev-only fallback — will never be used in production
        SECRET_KEY = 'dev-only-insecure-key-DO-NOT-USE-IN-PRODUCTION'
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY environment variable is required in production. '
            'Generate one with: python -c "from django.core.management.utils '
            'import get_random_secret_key; print(get_random_secret_key())"'
        )

# ── Allowed hosts ─────────────────────────────────────────────────────────────
# All hosts come from environment; no hardcoded domain names in code.
_hosts_env = _env('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _hosts_env.split(',') if h.strip()]

# Railway sets RAILWAY_PUBLIC_DOMAIN automatically
_railway_domain = _env('RAILWAY_PUBLIC_DOMAIN', '')
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)

# ── CSRF ──────────────────────────────────────────────────────────────────────
_csrf_env = _env('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(',') if o.strip()]
if _railway_domain:
    _railway_origin = f'https://{_railway_domain}'
    if _railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_railway_origin)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'apps.accounts',
    'apps.complex',
    'apps.clients',
    'apps.sales',
    'apps.payments',
    'apps.expenses',
    'apps.audit',
    'apps.dashboard',
    'apps.workers',
    'apps.materials',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.accounts.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
USE_SQLITE = _env('USE_SQLITE', 'False') == 'True'

_db_url = _env('DATABASE_URL') or (_env('PGHOST') and (
    f"postgresql://{_env('PGUSER')}:{_env('PGPASSWORD')}@"
    f"{_env('PGHOST')}:{_env('PGPORT', '5432')}/{_env('PGDATABASE', 'railway')}"
))

if _db_url:
    from urllib.parse import urlparse as _urlparse
    _u = _urlparse(_db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _u.path.lstrip('/'),
            'USER': _u.username,
            'PASSWORD': _u.password,
            'HOST': _u.hostname,
            'PORT': _u.port or 5432,
            'OPTIONS': {'connect_timeout': 10},
            'CONN_MAX_AGE': 60,
        }
    }
elif USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _env('DB_NAME', 'poytakht_crm'),
            'USER': _env('DB_USER', 'postgres'),
            'PASSWORD': _env('DB_PASSWORD', ''),
            'HOST': _env('DB_HOST', 'localhost'),
            'PORT': _env('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Dushanbe'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.CustomUser'
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ── Session & Cookie Security ─────────────────────────────────────────────────
SESSION_COOKIE_AGE = 3600 * 8          # 8 hours (was 10)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True          # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False            # JS needs CSRF for AJAX — keep False
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Security Headers ──────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True        # deprecated in newer Django but harmless
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'          # allow same-origin iframes (reports/PDF)
SECURE_REFERRER_POLICY = 'same-origin'

# ── Production-only Security ──────────────────────────────────────────────────
if not DEBUG:
    # Railway terminates SSL at the load balancer — trust X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Cookies must only be sent over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS — tells browsers to always use HTTPS for this domain
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # NOTE: Do NOT set SECURE_SSL_REDIRECT=True when behind Railway's proxy.
    # Railway handles HTTP→HTTPS redirect at the load balancer level.
    # Setting it in Django would cause an infinite redirect loop.

# ── Login Rate Limiting ───────────────────────────────────────────────────────
# Used by apps/accounts/views.py to block brute-force attempts.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# ── File Upload Security ──────────────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024    # 5 MB max in memory
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024    # 5 MB max POST body
MAX_UPLOAD_SIZE = 10 * 1024 * 1024               # 10 MB absolute max (checked in views)
ALLOWED_UPLOAD_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.webp',     # images
    '.pdf',                                        # documents
    '.doc', '.docx', '.xls', '.xlsx',             # office
]

# ── Caching (for rate limiting) ───────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'poytakht-crm-cache',
    }
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {'()': 'django.utils.log.RequireDebugTrue'},
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'console_debug': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.accounts': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

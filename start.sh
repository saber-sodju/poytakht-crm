#!/bin/sh
set -e

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Checking if users exist ==="
python manage.py shell -c "
from apps.accounts.models import CustomUser
count = CustomUser.objects.filter(role='director').count()
if count == 0:
    print('No director found — running seed_data to create demo accounts...')
    from django.core.management import call_command
    call_command('seed_data')
    print('Done.')
else:
    print(f'Found {count} director(s) — skipping seed_data.')
"

echo "=== Starting Gunicorn ==="
exec gunicorn core.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --error-logfile -

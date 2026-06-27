#!/bin/sh
set -e

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running database migrations ==="
python manage.py migrate --noinput

# Seed data (demo accounts) only when explicitly enabled.
# NEVER run in production — set RUN_SEED_DATA=1 only in local/staging environments.
if [ "${RUN_SEED_DATA:-0}" = "1" ]; then
  echo "=== Loading seed data (demo accounts) ==="
  python manage.py seed_data
else
  echo "=== Skipping seed data (production mode) ==="
fi

echo "=== Starting Gunicorn ==="
exec gunicorn core.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --error-logfile -

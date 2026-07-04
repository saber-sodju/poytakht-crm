#!/bin/sh
set -e

echo "=== Creating media directories ==="
mkdir -p media/construction media/layouts media/receipts media/expense_docs media/avatars

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running database migrations ==="
python manage.py migrate --noinput

# Create the first director from env vars if none exists (idempotent, prod-safe).
# Set INITIAL_DIRECTOR_USERNAME + INITIAL_DIRECTOR_PASSWORD in Railway variables.
echo "=== Ensuring director account exists ==="
python manage.py create_initial_director

# Demo data: ONLY when explicitly enabled (development / staging).
# NEVER set RUN_SEED_DATA=1 in production — it creates demo accounts
# with weak, publicly-known passwords (director / demo123456).
if [ "${RUN_SEED_DATA:-0}" = "1" ]; then
  echo "=== Loading seed data (demo accounts — DEV ONLY) ==="
  python manage.py seed_data
fi

# Non-destructive health check. We do NOT auto-seed demo data in production:
# that would inject weak default credentials. If there is no director, the
# operator must create one via INITIAL_DIRECTOR_* env vars (see README_PRODUCTION.md).
DIRECTOR_EXISTS=$(python manage.py shell -c "from apps.accounts.models import CustomUser; print(1 if CustomUser.objects.filter(role='director').exists() else 0)" | tail -1)
if [ "$DIRECTOR_EXISTS" = "0" ]; then
  echo "!!! WARNING: no director account exists."
  echo "!!! Set INITIAL_DIRECTOR_USERNAME and INITIAL_DIRECTOR_PASSWORD in the"
  echo "!!! environment and redeploy, or run 'python manage.py seed_data' locally."
  echo "!!! Refusing to auto-create demo accounts in production for security."
fi

echo "=== Starting Gunicorn ==="
exec gunicorn core.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --error-logfile -

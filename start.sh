#!/bin/sh
set -e

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running database migrations ==="
python manage.py migrate --noinput

# Create the first director from env vars if none exists (idempotent, prod-safe).
# Set INITIAL_DIRECTOR_USERNAME + INITIAL_DIRECTOR_PASSWORD in Railway variables.
echo "=== Ensuring director account exists ==="
python manage.py create_initial_director

# Demo data: ONLY when explicitly enabled (development / staging).
# Never set RUN_SEED_DATA=1 in production — it creates weak demo passwords.
if [ "${RUN_SEED_DATA:-0}" = "1" ]; then
  echo "=== Loading seed data (demo accounts) ==="
  python manage.py seed_data
fi

# SAFETY NET for ephemeral databases (SQLite without a volume):
# if after all of the above there is still no director, the DB is empty and
# nobody could log in at all. Seed demo data so the system stays accessible.
# Fix properly by attaching PostgreSQL (see README_PRODUCTION.md).
DIRECTOR_EXISTS=$(python manage.py shell -c "from apps.accounts.models import CustomUser; print(1 if CustomUser.objects.filter(role='director').exists() else 0)" | tail -1)
if [ "$DIRECTOR_EXISTS" = "0" ]; then
  echo "!!! WARNING: database has no director (ephemeral DB?) — seeding demo data"
  echo "!!! Attach PostgreSQL and set INITIAL_DIRECTOR_* vars for production."
  python manage.py seed_data
fi

echo "=== Starting Gunicorn ==="
exec gunicorn core.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 120 \
  --log-file - \
  --access-logfile - \
  --error-logfile -

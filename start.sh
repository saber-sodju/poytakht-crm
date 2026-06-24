#!/bin/sh
echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Loading seed data ==="
python manage.py seed_data

echo "=== Starting gunicorn ==="
exec gunicorn core.wsgi --bind "0.0.0.0:${PORT:-8000}" --workers 2 --log-file -

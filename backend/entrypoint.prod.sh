#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

# Hands off to whatever CMD was passed (gunicorn by default, per the
# Dockerfile - but docker-compose can override it, e.g. for celery).
exec "$@"

#!/bin/sh
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

# No collectstatic here - celery worker/beat never serve HTTP, so static
# files are irrelevant to them. Keeping it out avoids every container
# racing to write the same files to the same shared volume on startup.
exec "$@"

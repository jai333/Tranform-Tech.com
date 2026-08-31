#!/bin/bash
set -e

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Starting application server..."
exec uvicorn ats_crm_project.asgi:application --host 0.0.0.0 --port ${PORT:-8000} --workers 4

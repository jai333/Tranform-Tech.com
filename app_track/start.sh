#!/bin/bash

echo "==> Running database migrations (non-blocking)..."
python manage.py migrate --no-input || echo "WARNING: Migrations failed - continuing anyway"

echo "==> Starting application server on port ${PORT:-8000}..."
exec uvicorn ats_crm_project.asgi:application --host 0.0.0.0 --port "${PORT:-8000}" --workers 2

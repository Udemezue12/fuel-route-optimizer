#!/bin/bash
set -e

echo "▶️ Applying Django migrations..."
python manage.py makemigrations
python manage.py migrate
echo "✅ Migrations done."

echo "▶️ Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf


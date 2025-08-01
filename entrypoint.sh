#!/bin/bash
set -e

echo "▶️ Applying Django migrations..."
python manage.py makemigrations
python manage.py migrate
echo "✅ Migrations done."
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "🔄 Verifying Redis Cloud connection with Python..."
python -c "
import os
import redis
url = os.getenv('REDIS_URL')
try:
    r = redis.Redis.from_url(url)
    r.ping()
    print(f'✅ Redis connection successful to: {url}')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
"

echo "▶️ Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf


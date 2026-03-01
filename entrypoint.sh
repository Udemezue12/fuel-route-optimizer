#!/bin/bash
set -e



echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Static files collected."

echo "Verifying Redis Cloud connection..."
python - <<'PYCODE'
import os, redis
url = os.getenv("REDIS_URL")
try:
    r = redis.Redis.from_url(url)
    r.ping()
    print(f"✅ Redis connection successful to: {url}")
except Exception as e:
    print(f"Redis connection failed: {e}")
PYCODE

echo "Starting Supervisor to manage Uvicorn and Celery..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf

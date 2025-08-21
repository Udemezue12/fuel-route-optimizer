from __future__ import absolute_import, unicode_literals

import os
import sys

import django
from celery import Celery
from dotenv import load_dotenv
from kombu.exceptions import OperationalError

from fuel_route_api.log import logger

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_project.settings")
django.setup()


app = Celery(
    "fuel_project",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    task_always_eager=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)


try:
    logger.debug(" Testing Redis broker connection...")
    conn = app.connection()
    conn.ensure_connection(max_retries=3)
    logger.debug("Redis broker connection successful.")
except OperationalError as e:
    logger.error(f" Failed to connect to broker: {e}")
    raise SystemExit(1)

logger.debug(" Importing tasks...")
app.autodiscover_tasks(["fuel_route_api"])


if __name__ == "__main__":
    app.start()

from __future__ import absolute_import, unicode_literals

import os
import sys

import django
from celery import Celery
from dotenv import load_dotenv


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



from fuel_route_api.tasks import calculate_route_tasks
from fuel_route_api.tasks import send_verify_tasks


if __name__ == "__main__":
    app.start()

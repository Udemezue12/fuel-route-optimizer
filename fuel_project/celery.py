import os
from celery import Celery
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuel_project.settings')

import django
from django.apps import apps

if not apps.ready:
        django.setup()
from fuel_route_api.tasks import CalculateRouteTask 
app = Celery('fuel_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_url = os.getenv("REDIS_URL")
app.conf.result_backend = os.getenv("REDIS_URL")
app.autodiscover_tasks()


app.register_task(CalculateRouteTask())


app.conf.update(
    task_routes={
        'fuel_route_api.tasks.calculate_route_task': {'queue': 'route_calculation'},
    },
    timezone='UTC',
    enable_utc=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    task_time_limit=300,
    task_soft_time_limit=240,
    result_backend=os.getenv("REDIS_URL")
)
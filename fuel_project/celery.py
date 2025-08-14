import os
import signal
import time
from celery import Celery
from kombu.exceptions import OperationalError
from dotenv import load_dotenv

load_dotenv()


app = Celery(
    "fuel_project",
    broker=os.getenv('REDIS_URL'),
    backend=os.getenv('REDIS_URL'),
)


app.autodiscover_tasks()

app.conf.update(
    task_always_eager=False,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)

def handle_sigterm(*args):
    print("[Celery] SIGTERM received, waiting up to 300s for tasks to finish...")
    time.sleep(300)  # 5 minutes
    print("[Celery] Exiting after grace period.")
    os._exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
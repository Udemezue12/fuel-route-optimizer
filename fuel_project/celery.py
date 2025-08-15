import sys
import os
import logging
from celery import Celery
from kombu.exceptions import OperationalError
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_project.settings")

import django
django.setup()



# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---- Step 2: Create Celery app ----
app = Celery(
    "fuel_project",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    task_always_eager=False,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)

# ---- Step 3: Health check for broker ----
try:
    logger.info("🔌 Testing Redis broker connection...")
    conn = app.connection()
    conn.ensure_connection(max_retries=3)
    logger.info("✅ Redis broker connection successful.")
except OperationalError as e:
    logger.error(f"❌ Failed to connect to broker: {e}")
    raise SystemExit(1)

logger.info("⏳ Delaying heavy task imports until after broker check...")

# ---- Step 4: Lazy-load heavy tasks ----
def load_heavy_tasks():
    try:
        import fuel_route_api.tasks
        logger.info("✅ Heavy tasks loaded successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to load heavy tasks: {e}", exc_info=True)
        raise

@app.on_after_configure.connect
def import_tasks(sender, **kwargs):
    load_heavy_tasks()

# ---- Step 5: Placeholder lightweight tasks ----
from celery import shared_task

@shared_task(name="fuel_route_api.tasks.calculate_route_task", bind=True)
def calculate_route_task(self, *args, **kwargs):
    logger.info("📦 Importing heavy CalculateRouteTask...")
    from fuel_route_api.tasks import CalculateRouteTask
    heavy_task = CalculateRouteTask()
    return heavy_task.run(*args, **kwargs)

@shared_task(name="fuel_route_api.tasks.example_task", bind=True)
def example_task(self, name):
    import time
    time.sleep(1)
    return f"Hello, {name}!"

logger.info("✅ Task stubs registered successfully.")

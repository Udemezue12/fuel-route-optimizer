import os
import logging
from celery import Celery
from kombu.exceptions import OperationalError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Celery with only minimal settings
app = Celery(
    "fuel_project",
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
)

app.conf.update(
    task_always_eager=False,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
)

# Health check: test broker before loading tasks
try:
    logger.info("🔌 Testing Redis broker connection...")
    print(" Testing Redis broker connection...")
    conn = app.connection()
    conn.ensure_connection(max_retries=3)
    logger.info("✅ Redis broker connection successful.")
except OperationalError as e:
    logger.error(f"❌ Failed to connect to broker: {e}")
    print(f"❌ Failed to connect to broker: {e}")
    raise SystemExit(1)

logger.info("⏳ Delaying heavy task imports until after broker check...")
print("⏳ Delaying heavy task imports until after broker check...")


def load_heavy_tasks():
  
    try:
        import fuel_route_api.tasks  
        logger.info("✅ Heavy tasks loaded successfully.")
        print("✅ Heavy tasks loaded successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to load heavy tasks: {e}", exc_info=True)
        raise


# Only load heavy tasks when worker starts
@app.on_after_configure.connect
def import_tasks(sender, **kwargs):
    load_heavy_tasks()

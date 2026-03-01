import logging
from functools import wraps

from ninja.errors import HttpError as HTTPException

from .friendly_msg import get_friendly_message

logger = logging.getLogger(__name__)


def safe_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        request = None

        # safer detection
        for arg in list(args) + list(kwargs.values()):
            if hasattr(arg, "headers") and hasattr(arg, "method"):
                request = arg
                break

        try:
            return await func(*args, **kwargs)

        except HTTPException as e:
            if request:
                client_ip = getattr(request, "client", None)
                client_ip = client_ip.host if client_ip else "unknown"

                path = getattr(request, "url", None)
                path = path.path if path else "unknown"

                trace_id = request.headers.get("X-Request-ID", "none")

                logger.warning(
                    f"[HTTPException] TraceID={trace_id} | "
                    f"{e.status_code} - {path} from {client_ip}: {e.message}"
                )

            raise

        except Exception as e:
            if request:
                client_ip = getattr(request, "client", None)
                client_ip = client_ip.host if client_ip else "unknown"

                path = getattr(request, "url", None)
                path = path.path if path else "unknown"

                trace_id = request.headers.get("X-Request-ID", "none")

                logger.error(
                    f"[Unhandled Error] TraceID={trace_id} | "
                    f"in {func.__name__} | Path: {path} | "
                    f"Client: {client_ip} | Error: {e}",
                    exc_info=True,
                )
            else:
                logger.error(
                    f"[Unhandled Error] in {func.__name__}: {e}",
                    exc_info=True,
                )

            raise HTTPException(
                status_code=500,
                message=get_friendly_message(e),
            )

    return wrapper

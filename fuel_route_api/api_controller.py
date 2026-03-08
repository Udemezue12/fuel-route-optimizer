import logging

from ninja_extra import NinjaExtraAPI


from fuel_route_api.routes.route_controller_routes import RouteController
from fuel_route_api.routes.fuel_route import FuelRoutes
from fuel_route_api.routes.geocode_routes import GetAndGeocodeRoutes
from fuel_route_api.routes.user_routes import AuthController

from .tokens import TokenRequest

logger = logging.getLogger(__name__)

api = NinjaExtraAPI(
    title="Fuel Route Optimizer API",
    version="2.0.0",
    description="Optimized fuel route calculation",
)

api.register_controllers(
    TokenRequest,
    AuthController,
    FuelRoutes,
    RouteController,
    GetAndGeocodeRoutes
)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):

    trace_id = request.headers.get("X-Request-ID", "none")

    client_ip = request.META.get("REMOTE_ADDR", "unknown")

    logger.error(
        f"[GLOBAL ERROR] TraceID={trace_id} | "
        f"Path={request.path} | "
        f"Method={request.method} | "
        f"Client={client_ip} | "
        f"Error={exc}",
        exc_info=True,
    )

    return api.create_response(
#         request,
#         {"detail": get_friendly_message(exc)},
#         status=500,
#     )

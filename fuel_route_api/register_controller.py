from ninja_extra import NinjaExtraAPI

from .auth import AuthController
from .calculate_controller import CalculateRouteController
from .fuel_routes_list import FuelRoutes
from .mapbox_controller import MapboxController
from .tokens import TokenRequest

api = NinjaExtraAPI(
    title="Fuel Route Optimizer API",
    version="1.0.0",
    description="Optimized fuel route calculation with Celery and TomTom",
)

api.register_controllers(
    TokenRequest, AuthController, FuelRoutes, CalculateRouteController, MapboxController
)

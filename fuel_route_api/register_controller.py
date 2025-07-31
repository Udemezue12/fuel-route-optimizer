from ninja_extra import NinjaExtraAPI
from .auth import AuthController
from .tokens import TokenRequest
from .route_controller import RouteController
from .mapbox_controller import MapboxController
from .fuel_routes_list import FuelRoutes


api = NinjaExtraAPI( title="Fuel Route Optimizer API",
    version="1.0.0",
    description="Optimized fuel route calculation with Celery and TomTom")

api.register_controllers(TokenRequest, AuthController, FuelRoutes,
                         RouteController, MapboxController)

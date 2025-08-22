from ninja_extra import NinjaExtraAPI

from .auth import AuthController
from .fuel_routes_list import FuelRoutes
from .mapbox_controller import MapboxController
from .route_controller import RouteController
from .tokens import TokenRequest

api = NinjaExtraAPI(
    title="Fuel Route Optimizer API",
    version="1.0.0",
    description="Optimized fuel route calculation",
)

api.register_controllers(
    TokenRequest, AuthController, FuelRoutes, RouteController, MapboxController
)

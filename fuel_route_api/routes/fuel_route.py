from injector import inject
from ninja_extra import api_controller, http_get, paginate, permissions, throttle

from fuel_route_api.models.models import FuelStation
from fuel_route_api.core.pagination import CustomPaginatedOutput, CustomPagination
from fuel_route_api.schema.schema import AvaliableRouteSchema
from fuel_route_api.core.throttling import CustomAnonRateThrottle, CustomUserThrottle
from fuel_route_api.services.fuel_routes_service import FuelRoutesService

@api_controller(tags=["All Available Fuel and Route Coordinates"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class FuelRoutes:
    @inject
    def __init__(self):
        self.fuel_lists_service=FuelRoutesService()
        

    @http_get(
        "/v2/avaliable/routes",
        response=CustomPaginatedOutput[AvaliableRouteSchema],
        permissions=[permissions.IsAuthenticated],
    )
    @paginate(CustomPagination)
    async def route_list(self):
        return await self.fuel_lists_service.route_list()

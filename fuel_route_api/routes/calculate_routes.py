from fuel_route_api.core.throttling import CustomAnonRateThrottle, CustomUserThrottle
from ninja_extra import api_controller, http_post, throttle
from fuel_route_api.schema.schema import RouteRequest
from fuel_route_api.services.calculate_route_service import CalculateRouteService


@api_controller("/v2/routes", tags=["Calculate Geo Routes"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class CalculateRouteControllerRouter:
    @http_post("/real/routes")
    async def fetch_route_data(self, coord: RouteRequest):
        return await CalculateRouteService().fetch_route_data(coord)
    @http_post("/calculate")
    async def calculate_route_data(self, data: RouteRequest):
        return await CalculateRouteService().calculate_route_data(data)
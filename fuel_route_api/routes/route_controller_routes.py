from injector import inject
from ninja_extra import api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAuthenticated

from fuel_route_api.core.throttling import (CustomAnonRateThrottle,
                                            CustomUserThrottle)
from fuel_route_api.schema.schema import RouteRequest
from fuel_route_api.services.geoapify_controller_service import \
    GeoapifyControllerService


@api_controller(tags=["Calculate Routes Using Geaopify API"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class RouteController:
    @inject
    def __init__(self):
        self.route_controller_service = GeoapifyControllerService()

    @http_post("/calculate/routes", permissions=[IsAuthenticated])
    async def calculate(self, data: RouteRequest):
        return await self.route_controller_service.calculate(data=data)

    @http_get("/route/summary/result/{cache_key}", permissions=[IsAuthenticated])
    async def get_route_summary(self,  cache_key: str):
        return await self.route_controller_service.get_route_summary(cache_key=cache_key)

    @http_get("/route/geometry/result/{cache_key}", permissions=[IsAuthenticated])
    async def get_route_geometry(self,  cache_key: str):
        return await self.route_controller_service.get_route_geometry(cache_key=cache_key)

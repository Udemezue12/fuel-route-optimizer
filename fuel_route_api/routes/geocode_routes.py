from fuel_route_api.core.throttling import CustomAnonRateThrottle, CustomUserThrottle
from ninja_extra import ControllerBase, api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAuthenticated
from fuel_route_api.schema.schema import (
    MapboxGeocodeResponseSchema,
    MapboxRouteRequestSchema,
    MapboxRouteResponseSchema,
)
from fuel_route_api.services.gecode_service import GetAndGeocodeService


@api_controller(tags=["Routes"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class GetAndGeocodeRoutes(ControllerBase):
    def __init__(self):
        self.get_and_gecode_service=GetAndGeocodeService()

    @http_post(
        "/v2/get/route", response=MapboxRouteResponseSchema, permissions=[IsAuthenticated]
    )
    async def get_route(self,  data: MapboxRouteRequestSchema):
        return await self.get_and_gecode_service.get_route(data=data)

    @http_get(
        "/v2/get/geocode", response=MapboxGeocodeResponseSchema, permissions=[IsAuthenticated]
    )
    async def geocode(self,  address: str, city: str, state: str):
        return await self.get_and_gecode_service.geocode(address=address, city=city, state=state)

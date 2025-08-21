from ninja.errors import HttpError
from ninja_extra import ControllerBase, api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAuthenticated

from fuel_route_api.throttling import CustomAnonRateThrottle, CustomUserThrottle

from .dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies
from .route_service import GeoapifyService, TomTomService
from .schema import (
    GeocodeInputSchema,
    MapboxGeocodeResponseSchema,
    MapboxRouteRequestSchema,
    MapboxRouteResponseSchema,
)


@api_controller(tags=["Routes"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class MapboxController(ControllerBase):
    def __init__(self):
        self.service_routes = TomTomService(
            cache_deps=CacheDependencies(),
            cache_key_deps=CacheKeyDependencies(),
            deps=CRUDDependencies(),
        )
        self.geopapi_routes = GeoapifyService(
            cache_deps=CacheDependencies(), cache_key_deps=CacheKeyDependencies()
        )

    @http_post(
        "/route", response=MapboxRouteResponseSchema, permissions=[IsAuthenticated]
    )
    async def get_route(self, request, data: MapboxRouteRequestSchema):
        try:
            route_data = await self.geopapi_routes.get_geoapify_route(
                data, mapbox_format=True
            )
            return MapboxRouteResponseSchema(**route_data)
        except Exception as e:
            raise HttpError(500, f"Error getting route: {str(e)}")

    @http_get(
        "/geocode", response=MapboxGeocodeResponseSchema, permissions=[IsAuthenticated]
    )
    async def geocode(self, request, address: str, city: str, state: str):
        try:
            data = GeocodeInputSchema(address=address, city=city, state=state)
            result = await self.service_routes.geocode_address(data)
            return {"lat": result.lat, "lon": result.lon}
        except Exception as e:
            raise HttpError(500, f"Geocoding failed: {str(e)}")

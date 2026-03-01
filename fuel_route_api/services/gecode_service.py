from fuel_route_api.core.cache_dependencies import (AsyncCacheDependencies,
                                     CacheKeyDependencies)
from fuel_route_api.core.repo_dependencies import CRUDDependencies
from ninja.errors import HttpError
from fuel_route_api.schema.schema import GeocodeInputSchema, MapboxRouteResponseSchema

from .geoapify_service import GeoapifyServiceAsync
from .tomtom_service import TomTomService


class GetAndGeocodeService:
    def __init__(self):
        self.service_routes = TomTomService()
        self.geopapi_routes = GeoapifyServiceAsync()
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies(),
        self.deps = CRUDDependencies(),

    async def get_route(self, data):
        try:
            route_data = await self.geopapi_routes.get_geoapify_route(
                data, mapbox_format=True
            )
            return MapboxRouteResponseSchema(**route_data)
        except Exception as e:
            raise HttpError(500, f"Error getting route: {str(e)}")

    async def geocode(self, address: str, city: str, state: str):
        try:
            data = GeocodeInputSchema(address=address, city=city, state=state)
            result = await self.service_routes.geocode_address(data)
            return {"lat": result.lat, "lon": result.lon}
        except Exception as e:
            raise HttpError(500, f"Geocoding failed: {str(e)}")

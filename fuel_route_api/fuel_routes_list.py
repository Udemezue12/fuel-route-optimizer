from injector import inject
from ninja_extra import api_controller, http_get, paginate, permissions, throttle

from fuel_route_api.dependencies import (
    CacheDependencies,
    CacheKeyDependencies,
    CRUDDependencies,
)
from fuel_route_api.models import FuelStation
from fuel_route_api.pagination import CustomPaginatedOutput, CustomPagination
from fuel_route_api.schema import AvaliableRouteSchema
from fuel_route_api.throttling import CustomAnonRateThrottle, CustomUserThrottle


@api_controller(tags=["All Available Fuel and Route Coordinates"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class FuelRoutes:
    @inject
    def __init__(
        self,
        cache_deps: CacheDependencies,
        deps: CRUDDependencies,
        cache_key_deps: CacheKeyDependencies,
    ):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps
        self.deps = deps

    @http_get(
        "avaliable/routes",
        response=CustomPaginatedOutput[AvaliableRouteSchema],
        permissions=[permissions.IsAuthenticated],
    )
    @paginate(CustomPagination)
    async def route_list(self):
        deps = self.deps
        cache_deps = self.cache_deps
        cache_key = "route_list"
        stations = await cache_deps.get_from_cache(cache_key)
        if not stations:
            stations = await deps.get_lists(model=FuelStation)
            await cache_deps.set_from_cache(cache_key, stations)
        return stations

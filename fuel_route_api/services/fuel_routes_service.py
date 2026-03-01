from fuel_route_api.core.cache_dependencies import (
    AsyncCacheDependencies,
    CacheKeyDependencies,
)
from fuel_route_api.core.repo_dependencies import CRUDDependencies
from injector import inject
from fuel_route_api.models.models import FuelStation


class FuelRoutesService:
    @inject
    def __init__(self):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.deps = CRUDDependencies()

    async def route_list(self):
        deps = self.deps
        cache_deps = self.cache_deps
        cache_key = "route_list"
        stations = await cache_deps.get_from_cache(cache_key)
        if not stations:
            stations = await deps.get_lists(model=FuelStation)
            await cache_deps.set_from_cache(cache_key, stations)
        return stations

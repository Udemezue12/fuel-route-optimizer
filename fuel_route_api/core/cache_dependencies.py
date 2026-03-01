import json
from hashlib import md5

from asgiref.sync import sync_to_async
from django.core.cache import cache


class AsyncCacheDependencies:
    async def get_from_cache(self, key):
        return await sync_to_async(cache.get, thread_sensitive=False)(key)

    async def add_from_cache(self, key, value, timeout=600):
        return await sync_to_async(
            cache.add,
            thread_sensitive=False
        )(key, value, timeout)

    async def set_from_cache(self, key, value, timeout=60 * 10):
        return await sync_to_async(cache.set, thread_sensitive=False)(key, value, timeout)

    async def delete_from_cache(self, key):
        return await sync_to_async(cache.delete, thread_sensitive=False)(key)


class SyncCacheDependencies:
    def get_from_cache(self, key):
        return cache.get(key)

    def add_to_cache(self, key, value, timeout=600):
        return cache.add(key, value, timeout=timeout)

    def set_from_cache(self, key, value, timeout=60 * 10):
        return cache.set(key, value, timeout=timeout)

    def delete_from_cache(self, key):
        return cache.delete(key)


class CacheKeyDependencies:
    async def generate_cache_key(self, data: dict) -> str:
        return md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

    def sync_generate_cache_key(self, data: dict) -> str:
        return md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

    async def validate_usa_coordinates(self, latitude: float, longitude: float) -> bool:
        usa_bounds = {
            "lat_min": 24.396308,
            "lat_max": 49.384358,
            "lon_min": -125.0,
            "lon_max": -66.93457,
        }
        return (
            usa_bounds["lat_min"] <= latitude <= usa_bounds["lat_max"]
            and usa_bounds["lon_min"] <= longitude <= usa_bounds["lon_max"]
        )

    def sync_validate_usa_coordinates(self, latitude: float, longitude: float) -> bool:
        usa_bounds = {
            "lat_min": 24.396308,
            "lat_max": 49.384358,
            "lon_min": -125.0,
            "lon_max": -66.93457,
        }
        return (
            usa_bounds["lat_min"] <= latitude <= usa_bounds["lat_max"]
            and usa_bounds["lon_min"] <= longitude <= usa_bounds["lon_max"]
        )

    async def _generate_cache_key(
        self, start_lat, start_lon, finish_lat, finish_lon, route_points=None
    ):
        base_key = f"route_{start_lat}_{start_lon}_{finish_lat}_{finish_lon}"
        if route_points:
            coords = [(p.latitude, p.longitude) for p in route_points]
            hash_part = md5(
                json.dumps(coords, sort_keys=True).encode("utf-8")
            ).hexdigest()
            return f"{base_key}_{hash_part}"
        return base_key

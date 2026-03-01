import logging
import ssl
from typing import Dict

import aiohttp
import certifi
from fuel_route_api.core.cache_dependencies import AsyncCacheDependencies, CacheKeyDependencies
from fuel_route_api.core.env import (
    MAPBOX_API_KEY,
    MAPBOX_BASE_URL,
)
from fuel_route_api.schema.schema import RouteRequestSchema

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


ssl_context = ssl.create_default_context(cafile=certifi.where())


class MapboxService:
    def __init__(self):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()

    async def get_mapbox_route(self, data: RouteRequestSchema) -> Dict:
        cache_key = await self.cache_key_deps.generate_cache_key(
            {
                "start": [data.start_lat, data.start_lon],
                "finish": [data.finish_lat, data.finish_lon],
            }
        )

        cached_route = await self.cache_deps.get_from_cache(cache_key)
        if cached_route:
            return cached_route

        url = f"{MAPBOX_BASE_URL}/directions/v5/mapbox/driving/{data.start_lon},{data.start_lat};{data.finish_lon},{data.finish_lat}"
        params = {
            "access_token": MAPBOX_API_KEY,
            "geometries": "geojson",
            "overview": "full",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception("Failed to fetch route from Mapbox API")

                route_data = await response.json()
                coordinates = route_data["routes"][0]["geometry"]["coordinates"]
                route_points = [
                    {"latitude": lat, "longitude": lon} for lon, lat in coordinates
                ]

                normalized_data = {
                    "routes": [
                        {
                            "summary": {
                                "lengthInMeters": route_data["routes"][0]["distance"]
                            },
                            "points": route_points,
                        }
                    ]
                }

                await self.cache_deps.set_from_cache(
                    cache_key, normalized_data, timeout=3600
                )
                return normalized_data

    async def geocode_address(
        self, address: str, city: str, state: str
    ) -> tuple[float, float]:
        query_parts = [part for part in [address, city, state, "USA"] if part]
        query = ", ".join(query_parts)
        url = f"{MAPBOX_BASE_URL}/geocoding/v5/mapbox.places/{query}.json"

        params = {
            "access_token": MAPBOX_API_KEY,
            "limit": 1,
            "types": "address,place,poi",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(
                        f"Mapbox returned status {response.status} for query: {query}"
                    )

                data = await response.json()
                if not data.get("features"):
                    raise Exception(
                        f"No results returned for geocode query: {query}")

                coords = data["features"][0]["center"]
                return coords[1], coords[0]

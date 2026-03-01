import ssl
from typing import Dict
import urllib
import aiohttp
import certifi
from fuel_route_api.core.env import (
    TOMTOM_API_KEY,
    TOMTOM_BASE_URL,
)
from fuel_route_api.core.repo_dependencies import CRUDDependencies
from injector import inject
from ninja.errors import HttpError
from fuel_route_api.schema.schema import (
    CoordinateSchema,
    GeocodeInputSchema,
    GeocodeOutputSchema,
)

from fuel_route_api.core.cache_dependencies import (
    AsyncCacheDependencies,
    CacheKeyDependencies,
)

ssl_context = ssl.create_default_context(cafile=certifi.where())


class TomTomService:
    @inject
    def __init__(self):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.deps = CRUDDependencies()

    async def get_tomtom_route(self, data: CoordinateSchema) -> Dict:
        if not await self.cache_key_deps.validate_usa_coordinates(
            data.start_lat, data.start_lon
        ):
            raise HttpError(
                400, "Invalid start coordinates (not within USA bounds).")
        if not await self.cache_key_deps.validate_usa_coordinates(
            data.finish_lat, data.finish_lon
        ):
            raise HttpError(
                400, "Invalid finish coordinates (not within USA bounds).")

        cache_key = await self.cache_key_deps.generate_cache_key(
            {
                "start": [data.start_lat, data.start_lon],
                "finish": [data.finish_lat, data.finish_lon],
            }
        )

        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            return cached

        url = f"{TOMTOM_BASE_URL}/routing/1/calculateRoute/{data.start_lat},{data.start_lon}:{data.finish_lat},{data.finish_lon}/json"

        params = {
            "travelMode": "car",
            "routeType": "eco",
            "routeRepresentation": "polyline",
            "computeTravelTimeFor": "all",
            "vehicleEngineType": "combustion",
            "vehicleCommercial": "false",
            "avoid": "unpavedRoads",
            "constantSpeedConsumptionInLitersPerHundredkm": "50:6.5,100:7.5",
            "vehicleWeight": "1600",  # A
        }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url, params=params) as response:
                route_data = await response.json()

                if response.status != 200:

                    raise HttpError(
                        502, f"TomTom API failed with status {response.status}"
                    )

                if "error" in route_data:

                    raise HttpError(
                        502, route_data["error"].get(
                            "message", "Unknown routing error")
                    )

                if "routes" not in route_data or not route_data["routes"]:

                    raise HttpError(
                        502, "No route found for the specified coordinates."
                    )

                first_route = route_data["routes"][0]
                if "summary" not in first_route or "points" not in first_route:

                    raise ValueError(
                        "TomTom route missing 'summary' or 'points' data")

                await self.cache_deps.set_from_cache(cache_key, route_data)
                return route_data

    async def geocode_address(self, data: GeocodeInputSchema) -> GeocodeOutputSchema:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            address = data.address.strip('" ').strip()
            city = data.city.strip('" ').strip()
            state = data.state.strip('" ').strip()
            raw_query = f"{address}, {city}, {state}, USA"
            query = urllib.parse.quote(raw_query)
            url = f"{TOMTOM_BASE_URL}/search/2/geocode/{query}.json"
            params = {"key": TOMTOM_API_KEY}

            async with session.get(url, params=params) as response:
                geocode_data = await response.json()
                if response.status != 200:
                    print(f" Geocoding failed: {response.status} - {geocode_data}")
                    raise HttpError(502, f"Failed to geocode address: {query}")

                if not geocode_data.get("results"):
                    print(f" No geocoding results for: {query}")
                    raise HttpError(404, "No results found for this address")

                position = geocode_data["results"][0]["position"]
                return GeocodeOutputSchema(lat=position["lat"], lon=position["lon"])

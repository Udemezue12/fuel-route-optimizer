import logging
from typing import Dict

import aiohttp
from injector import inject
from ninja.errors import HttpError

from .dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies
from .env import (
    GEOAPIFY_API_KEY,
    GEOAPIFY_BASE_URL,
    MAPBOX_API_KEY,
    MAPBOX_BASE_URL,
    TOMTOM_API_KEY,
    TOMTOM_BASE_URL,
)
from .schema import (
    CoordinateSchema,
    GeocodeInputSchema,
    GeocodeOutputSchema,
    RouteRequestSchema,
)


class MapboxService:
    def __init__(
        self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies
    ):
        self.cache_key_deps = cache_key_deps
        self.cache_deps = cache_deps

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
                    raise Exception(f"No results returned for geocode query: {query}")

                coords = data["features"][0]["center"]
                return coords[1], coords[0]


class TomTomService:
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

    async def get_tomtom_route(self, data: CoordinateSchema) -> Dict:
        if not await self.cache_key_deps.validate_usa_coordinates(
            data.start_lat, data.start_lon
        ):
            raise HttpError(400, "Invalid start coordinates (not within USA bounds).")
        if not await self.cache_key_deps.validate_usa_coordinates(
            data.finish_lat, data.finish_lon
        ):
            raise HttpError(400, "Invalid finish coordinates (not within USA bounds).")

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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                route_data = await response.json()

                if response.status != 200:
                    print(f"❌ TomTom API Error ({response.status}): {route_data}")
                    raise HttpError(
                        502, f"TomTom API failed with status {response.status}"
                    )

                if "error" in route_data:
                    print(f"🚫 TomTom Routing Error: {route_data['error']}")
                    raise HttpError(
                        502, route_data["error"].get("message", "Unknown routing error")
                    )

                if "routes" not in route_data or not route_data["routes"]:
                    print("⚠️ No route returned from TomTom.")
                    raise HttpError(
                        502, "No route found for the specified coordinates."
                    )

                first_route = route_data["routes"][0]
                if "summary" not in first_route or "points" not in first_route:
                    print(f"⚠️ Incomplete route data: {first_route}")
                    raise ValueError("TomTom route missing 'summary' or 'points' data")

                await self.cache_deps.set_from_cache(cache_key, route_data)
                return route_data

    async def geocode_address(self, data: GeocodeInputSchema) -> GeocodeOutputSchema:
        async with aiohttp.ClientSession() as session:
            query = f"{data.address}, {data.city}, {data.state}, USA"
            url = f"{TOMTOM_BASE_URL}/search/2/geocode/{query}.json"
            params = {"key": TOMTOM_API_KEY}

            async with session.get(url, params=params) as response:
                geocode_data = await response.json()
                if response.status != 200:
                    print(f"❌ Geocoding failed: {response.status} - {geocode_data}")
                    raise HttpError(502, f"Failed to geocode address: {query}")

                if not geocode_data.get("results"):
                    print(f"📭 No geocoding results for: {query}")
                    raise HttpError(404, "No results found for this address")

                position = geocode_data["results"][0]["position"]
                return GeocodeOutputSchema(lat=position["lat"], lon=position["lon"])


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


class GeoapifyService:
    def __init__(
        self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies
    ):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps

    async def get_geoapify_route(
        self, data: CoordinateSchema, mapbox_format: bool = False
    ) -> Dict:
        logger.info(
            f"📍 Validating coordinates: start=({data.start_lat}, {data.start_lon}), finish=({data.finish_lat}, {data.finish_lon})"
        )

        if not await self.cache_key_deps.validate_usa_coordinates(
            data.start_lat, data.start_lon
        ):
            logger.error("❌ Invalid start coordinates (not within USA bounds).")
            raise HttpError(400, "Invalid start coordinates (not within USA bounds).")
        if not await self.cache_key_deps.validate_usa_coordinates(
            data.finish_lat, data.finish_lon
        ):
            logger.error("❌ Invalid finish coordinates (not within USA bounds).")
            raise HttpError(400, "Invalid finish coordinates (not within USA bounds).")

        cache_key = await self.cache_key_deps.generate_cache_key(
            {
                "start": [data.start_lat, data.start_lon],
                "finish": [data.finish_lat, data.finish_lon],
            }
        )
        logger.info(f"🗄 Checking cache for key: {cache_key}")
        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info("✅ Cache hit for route. Returning cached result.")
            return cached

        url = GEOAPIFY_BASE_URL
        params = {
            "apiKey": GEOAPIFY_API_KEY,
            "mode": "drive",
            "waypoints": f"{data.start_lat},{data.start_lon}|{data.finish_lat},{data.finish_lon}",
            "details": "route_details",
        }
        logger.info(
            f"🌐 Requesting route from Geoapify API: {url} with params {params}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                route_data = await response.json()
                logger.debug(f"📦 Full Geoapify API Response: {route_data}")

                if response.status != 200:
                    logger.error(
                        f"❌ Geoapify API failed with status {response.status}"
                    )
                    if response.status == 403:
                        raise HttpError(
                            502,
                            "Geoapify API access forbidden. Check API key or free tier limits.",
                        )
                    raise HttpError(
                        502, f"Geoapify API failed with status {response.status}"
                    )

                if "error" in route_data:
                    logger.error(f"❌ Geoapify error: {route_data['error']}")
                    raise HttpError(
                        502, route_data["error"].get("message", "Unknown routing error")
                    )

                if "features" not in route_data or not route_data["features"]:
                    logger.error("❌ No route found for the given coordinates.")
                    raise HttpError(
                        400,
                        "No route found for the specified coordinates or parameters.",
                    )

                first_feature = route_data["features"][0]
                if "geometry" not in first_feature or "properties" not in first_feature:
                    logger.error(
                        "❌ Missing geometry or properties in Geoapify response."
                    )
                    raise ValueError(
                        "Geoapify route missing 'geometry' or 'properties' data"
                    )

                distance_meters = first_feature["properties"].get("distance", 0)
                time_seconds = first_feature["properties"].get("time", 0)
                coordinates = (
                    first_feature["geometry"]["coordinates"][0]
                    if first_feature["geometry"]["coordinates"]
                    else []
                )
                segments = (
                    first_feature["properties"].get("legs", [{}])[0].get("steps", [])
                )

                fuel_efficiency_liters_per_km = 0.078
                for segment in segments:
                    if (
                        segment.get("road_class") in ["secondary", "tertiary"]
                        or segment.get("surface") == "unpaved"
                    ):
                        fuel_efficiency_liters_per_km += 0.01
                fuel_consumption_liters = (
                    distance_meters / 1000
                ) * fuel_efficiency_liters_per_km

                logger.info(
                    f"📏 Distance: {distance_meters} meters | ⏱ Time: {time_seconds} sec | ⛽ Fuel: {fuel_consumption_liters:.2f} liters"
                )

                tomtom_structure = {
                    "routes": [
                        {
                            "summary": {
                                "lengthInMeters": distance_meters,
                                "travelTimeInSeconds": time_seconds,
                                "trafficDelayInSeconds": 0,
                                "fuelConsumptionInLiters": round(
                                    fuel_consumption_liters, 2
                                ),
                            },
                            "points": [
                                {"latitude": coord[1], "longitude": coord[0]}
                                for coord in coordinates
                            ],
                        }
                    ]
                }

                mapbox_structure = {
                    "routes": [
                        {
                            "geometry": {
                                "coordinates": coordinates,
                                "type": "LineString",
                            },
                            "distance": distance_meters,
                            "duration": time_seconds,
                            "fuelConsumptionInLiters": round(
                                fuel_consumption_liters, 2
                            ),
                        }
                    ]
                }

                result = mapbox_structure if mapbox_format else tomtom_structure
                logger.info("🗄 Caching route result...")
                await self.cache_deps.set_from_cache(cache_key, result)
                logger.info("✅ Route calculation completed successfully.")
                return result

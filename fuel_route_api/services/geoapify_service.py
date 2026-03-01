import logging
import ssl
from typing import Dict

import aiohttp
import certifi
import requests
from fuel_route_api.core.cache_dependencies import (
    AsyncCacheDependencies,
    CacheKeyDependencies,
    SyncCacheDependencies,
)
from fuel_route_api.core.env import GEOAPIFY_API_KEY, GEOAPIFY_BASE_URL
from ninja.errors import HttpError
from fuel_route_api.schema.schema import (
    CoordinateSchema,
    GeocodeInputSchema,
    GeocodeOutputSchema,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


ssl_context = ssl.create_default_context(cafile=certifi.where())

logger = logging.getLogger(__name__)

class GeoapifyServiceAsync:
    def __init__(self):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()

    async def get_geoapify_route(
        self, data: CoordinateSchema, mapbox_format: bool = False
    ) -> Dict:
        

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

        url = f"{GEOAPIFY_BASE_URL}/routing"
        params = {
            "apiKey": GEOAPIFY_API_KEY,
            "mode": "drive",
            "waypoints": f"{data.start_lat},{data.start_lon}|{data.finish_lat},{data.finish_lon}",
            "details": "route_details",
        }
        

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                route_data = await response.json()
               

                if response.status != 200:
                    
                    if response.status == 403:
                        raise HttpError(
                            502,
                            "Geoapify API access forbidden. Check API key or free tier limits.",
                        )
                    raise HttpError(
                        502, f"Geoapify API failed with status {response.status}"
                    )

                if "error" in route_data:
                    
                    raise HttpError(
                        502, route_data["error"].get(
                            "message", "Unknown routing error")
                    )

                if "features" not in route_data or not route_data["features"]:
                    
                    raise HttpError(
                        400,
                        "No route found for the specified coordinates or parameters.",
                    )

                first_feature = route_data["features"][0]
                if "geometry" not in first_feature or "properties" not in first_feature:
                    
                    raise ValueError(
                        "Geoapify route missing 'geometry' or 'properties' data"
                    )

                distance_meters = first_feature["properties"].get(
                    "distance", 0)
                time_seconds = first_feature["properties"].get("time", 0)
                coordinates = (
                    first_feature["geometry"]["coordinates"][0]
                    if first_feature["geometry"]["coordinates"]
                    else []
                )
                segments = (
                    first_feature["properties"].get(
                        "legs", [{}])[0].get("steps", [])
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

    async def geocode_address(self, data: GeocodeInputSchema) -> GeocodeOutputSchema:
        async with aiohttp.ClientSession() as session:

            address = data.address.strip('" ').strip()
            city = data.city.strip('" ').strip()
            state = data.state.strip('" ').strip()

            raw_query = f"{address}, {city}, {state}, USA"

            params = {
                "text": raw_query,
                "format": "json",
                "apiKey": GEOAPIFY_API_KEY,
            }
            url = f"{GEOAPIFY_BASE_URL}/geocode/search"

            async with session.get(url, params=params) as response:
                geocode_data = await response.json()

                if response.status != 200:
                    print(
                        f"Geocoding failed: {response.status} - {geocode_data}")
                    raise HttpError(502, "Failed to geocode address")

                if not geocode_data.get("results"):
                    print(f"No geocoding results for: {raw_query}")
                    raise HttpError(404, "No results found for this address")

                position = geocode_data["results"][0]
                return GeocodeOutputSchema(
                    lat=position["lat"],
                    lon=position["lon"]
                )

class GeoapifyServiceSync:
    def __init__(self):
        self.cache_deps = SyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()

    
    def get_geoapify_route(
        self, data: CoordinateSchema, mapbox_format: bool = False
    ) -> Dict:

        
        if not self.cache_key_deps.sync_validate_usa_coordinates(
            data.start_lat, data.start_lon
        ):
            raise HttpError(400, "Invalid start coordinates (not within USA bounds).")

        if not self.cache_key_deps.sync_validate_usa_coordinates(
            data.finish_lat, data.finish_lon
        ):
            raise HttpError(400, "Invalid finish coordinates (not within USA bounds).")

       
        cache_key = self.cache_key_deps.sync_generate_cache_key(
            {
                "start": [data.start_lat, data.start_lon],
                "finish": [data.finish_lat, data.finish_lon],
            }
        )

       
        cached = self.cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info("Cache hit for route. Returning cached result.")
            return cached

       
        url = f"{GEOAPIFY_BASE_URL}/routing"
        params = {
            "apiKey": GEOAPIFY_API_KEY,
            "mode": "drive",
            "waypoints": f"{data.start_lat},{data.start_lon}|{data.finish_lat},{data.finish_lon}",
            "details": "route_details",
        }

        logger.info(f"Requesting route from Geoapify API...")

        response = requests.get(url, params=params, timeout=15)
        route_data = response.json()

        if response.status_code != 200:
            if response.status_code == 403:
                raise HttpError(
                    502,
                    "Geoapify API access forbidden. Check API key or free tier limits.",
                )
            raise HttpError(
                502, f"Geoapify API failed with status {response.status_code}"
            )

        if "error" in route_data:
            raise HttpError(
                502,
                route_data["error"].get("message", "Unknown routing error"),
            )

        if "features" not in route_data or not route_data["features"]:
            raise HttpError(
                400,
                "No route found for the specified coordinates or parameters.",
            )

        first_feature = route_data["features"][0]

        if "geometry" not in first_feature or "properties" not in first_feature:
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

        # Fuel efficiency calculation
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

       
        logger.info("Caching route result...")
        self.cache_deps.set_from_cache(cache_key, result, timeout=3600)

        logger.info("Route calculation completed successfully.")
        return result

   
    def geocode_address(self, data: GeocodeInputSchema) -> GeocodeOutputSchema:

        address = data.address.strip('" ').strip()
        city = data.city.strip('" ').strip()
        state = data.state.strip('" ').strip()

        raw_query = f"{address}, {city}, {state}, USA"

        params = {
            "text": raw_query,
            "format": "json",
            "apiKey": GEOAPIFY_API_KEY,
        }

        url = f"{GEOAPIFY_BASE_URL}/geocode/search"

        response = requests.get(url, params=params, timeout=10)
        geocode_data = response.json()

        if response.status_code != 200:
            raise HttpError(502, "Failed to geocode address")

        if not geocode_data.get("results"):
            raise HttpError(404, "No results found for this address")

        position = geocode_data["results"][0]

        return GeocodeOutputSchema(
            lat=position["lat"],
            lon=position["lon"],
        )
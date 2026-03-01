import logging

import httpx
from celery import shared_task

from fuel_route_api.core.cache_dependencies import (CacheKeyDependencies,
                                                    SyncCacheDependencies)
from fuel_route_api.core.compression import compress_data
from fuel_route_api.schema.schema import CoordinateSchema, RouteRequest
from fuel_route_api.services.fuel_stop_service import FuelStopService
from fuel_route_api.services.geoapify_service import GeoapifyServiceSync

logger = logging.getLogger(__name__)


@shared_task(
    name="calculate_geo_routes",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def calculate_route_task(data: dict):

    try:
        data_model = RouteRequest(**data)

        cache_deps = SyncCacheDependencies()
        cache_key_deps = CacheKeyDependencies()
        geoapify_service = GeoapifyServiceSync()
        fuel_service = FuelStopService()

        validate_coords = cache_key_deps.sync_validate_usa_coordinates

        if not validate_coords(data_model.start_lat, data_model.start_lon):
            raise ValueError(
                "Invalid start coordinates (not within USA bounds).")

        if not validate_coords(data_model.finish_lat, data_model.finish_lon):
            raise ValueError(
                "Invalid finish coordinates (not within USA bounds).")

        coordinate_schema = CoordinateSchema(
            start_lat=data_model.start_lat,
            start_lon=data_model.start_lon,
            finish_lat=data_model.finish_lat,
            finish_lon=data_model.finish_lon,
        )

        route_data = geoapify_service.get_geoapify_route(
            coordinate_schema,
            mapbox_format=False,
        )

        route_points = [
            {"latitude": p["latitude"], "longitude": p["longitude"]}
            for p in route_data["routes"][0]["points"]
        ]

        total_distance_miles = (
            route_data["routes"][0]["summary"]["lengthInMeters"] / 1609.34
        )

        fuel_stops = fuel_service.sync_find_optimal_fuel_stops(route_points)
        total_fuel_cost = fuel_service.sync_calculate_fuel_cost(
            total_distance_miles, fuel_stops
        )
        cost_summary = fuel_service.sync_calculate_fuel_costs(
            total_distance_miles, fuel_stops
        )

        geometry_data = {
            "route": route_points
        }

        summary_data = {
            "fuel_stops": fuel_stops,
            "total_fuel_cost": total_fuel_cost,
            "total_distance_miles": round(total_distance_miles, 2),
            "number_of_stops": cost_summary["number_of_stops"],
            "average_price": cost_summary["average_price"],
            "gallons_needed": cost_summary["gallons_needed"],
            "success": True,
        }

        cache_key = cache_key_deps.sync_generate_cache_key(data_model.dict())

        summary_key = f"route:{cache_key}:summary"
        geometry_key = f"route:{cache_key}:geometry"

        cache_deps.set_from_cache(
            summary_key,
            compress_data(summary_data),
            timeout=3600,
        )

        cache_deps.set_from_cache(
            geometry_key,
            compress_data(geometry_data),
            timeout=3600,
        )

        

        return {"cache_key": cache_key, "status": "done"}

    except Exception as e:
        
        return {"success": False, "error": str(e)}

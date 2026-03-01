from fuel_route_api.core.cache_dependencies import (
    AsyncCacheDependencies,
    CacheKeyDependencies,
)

from fuel_route_api.core.repo_dependencies import CRUDDependencies

from .fuel_stop_service import FuelStopService
from .geoapify_service import GeoapifyServiceAsync


class CalculateRouteService:
    def __init__(self):

        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.crud_deps = CRUDDependencies()
        self.geoapify_service = GeoapifyServiceAsync()
        self.fuel_service = FuelStopService()

    async def fetch_route_data(self, coord):
        
        route_data = await self.geoapify_service.get_geoapify_route(
            coord, mapbox_format=False
        )

        summary = route_data["routes"][0]["summary"]
        distance_m = summary.get("lengthInMeters", 0)
        duration_s = summary.get("travelTime", 0)
        distance_miles = round(distance_m / 1609.34, 2)

        route_points = [
            [p["longitude"], p["latitude"]] for p in route_data["routes"][0]["points"]
        ]

        fuel_stops = await self.fuel_service.find_current_optimal_fuel_stops(
            route_points
        )
        cost_summary = await self.fuel_service.calculate_fuel_costs(
            distance_miles, fuel_stops
        )

        return {
            "final_result": {
                "fuel_stops": fuel_stops,
                "number_of_stops": cost_summary["number_of_stops"],
                "average_price": cost_summary["average_price"],
                "gallons_needed": cost_summary["gallons_needed"],
                "total_cost": cost_summary["total_cost"],
                "distance_miles": distance_miles,
                "duration_seconds": duration_s,
            }
        }

    async def calculate_route_data(self, data):
        try:

            if not await self.cache_key_deps.validate_usa_coordinates(
                data.start_lat, data.start_lon
            ):
                raise ValueError(
                    "Invalid start coordinates (not within USA bounds).")
            if not await self.cache_key_deps.validate_usa_coordinates(
                data.finish_lat, data.finish_lon
            ):
                raise ValueError(
                    "Invalid finish coordinates (not within USA bounds).")

            route_data = await self.geoapify_service.get_geoapify_route(
                data, mapbox_format=False
            )

            route_points = [
                {"latitude": p["latitude"], "longitude": p["longitude"]}
                for p in route_data["routes"][0]["points"]
            ]
            total_distance_miles = (
                route_data["routes"][0]["summary"]["lengthInMeters"] / 1609.34
            )

            fuel_stops = await self.fuel_service.find_optimal_fuel_stops(route_points)

            total_fuel_cost = await self.fuel_service.calculate_fuel_cost(
                total_distance_miles, fuel_stops
            )
            cost_summary = await self.fuel_service.calculate_fuel_costs(
                total_distance_miles, fuel_stops
            )

            result = {
                "route": route_points,
                "fuel_stops": fuel_stops,
                "total_fuel_cost": total_fuel_cost,
                "total_distance_miles": round(total_distance_miles, 2),
                "number_of_stops": cost_summary["number_of_stops"],
                "average_price": cost_summary["average_price"],
                "gallons_needed": cost_summary["gallons_needed"],
                "success": True,
            }

            cache_key = f"route_result_{data.start_lat}_{data.start_lon}_{data.finish_lat}_{data.finish_lon}"
            await self.cache_deps.set_from_cache(cache_key, result, timeout=3600)

            return result

        except Exception as e:

            return {"success": False, "error": str(e)}

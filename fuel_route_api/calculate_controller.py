from ninja_extra import api_controller, http_post, throttle

from fuel_route_api.dependencies import (
    CacheDependencies,
    CacheKeyDependencies,
    CRUDDependencies,
)
from fuel_route_api.fuel_stop_service import FuelStopService
from fuel_route_api.route_service import GeoapifyService

from .log import logger
from .schema import RouteRequest
from .throttling import CustomAnonRateThrottle, CustomUserThrottle


@api_controller("/routes", tags=["Calculate Routes"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class CalculateRouteController:
    def __init__(self):
        logger.debug(" Setting up service dependencies (API mode)...")
        self.cache_deps = CacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.crud_deps = CRUDDependencies()
        self.geoapify_service = GeoapifyService(
            cache_deps=self.cache_deps, cache_key_deps=self.cache_key_deps
        )
        self.fuel_service = FuelStopService(self.cache_deps, self.cache_key_deps)
        logger.debug(" Services initialized successfully (API mode).")

    @http_post("/real/routes")
    async def fetch_route_data(self, coord: RouteRequest):
        logger.info(" Calling Geoapify API...")
        route_data = await self.geoapify_service.get_geoapify_route(
            coord, mapbox_format=False
        )

        summary = route_data["routes"][0]["summary"]
        distance_m = summary.get("lengthInMeters", 0)
        duration_s = summary.get("travelTime", 0)
        distance_miles = round(distance_m / 1609.34, 2)

        logger.info(
            f" Distance: {distance_m} m | ⏱ {duration_s} sec | ~{distance_miles} miles"
        )

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

    @http_post("/calculate")
    async def calculate_route_data(self, data: RouteRequest):
        try:
            logger.debug(" Validating coordinates...")
            if not await self.cache_key_deps.validate_usa_coordinates(
                data.start_lat, data.start_lon
            ):
                raise ValueError("Invalid start coordinates (not within USA bounds).")
            if not await self.cache_key_deps.validate_usa_coordinates(
                data.finish_lat, data.finish_lon
            ):
                raise ValueError("Invalid finish coordinates (not within USA bounds).")

            logger.debug(" Fetching route from Geoapify API...")
            route_data = await self.geoapify_service.get_geoapify_route(
                data, mapbox_format=False
            )
            logger.debug(
                f" Route fetched. Summary: {route_data['routes'][0]['summary']}"
            )

            route_points = [
                {"latitude": p["latitude"], "longitude": p["longitude"]}
                for p in route_data["routes"][0]["points"]
            ]
            total_distance_miles = (
                route_data["routes"][0]["summary"]["lengthInMeters"] / 1609.34
            )
            logger.debug(f"📏 Total route distance: {total_distance_miles:.2f} miles")

            logger.debug(" Finding optimal fuel stops...")
            fuel_stops = await self.fuel_service.find_optimal_fuel_stops(route_points)
            logger.debug(f"Found {len(fuel_stops)} optimal fuel stops.")

            logger.debug(" Calculating total fuel cost...")
            total_fuel_cost = await self.fuel_service.calculate_fuel_cost(
                total_distance_miles, fuel_stops
            )
            cost_summary = await self.fuel_service.calculate_fuel_costs(
                total_distance_miles, fuel_stops
            )
            logger.debug(f" Estimated total fuel cost: ${total_fuel_cost:.2f}")

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

            logger.debug(" Saving result to cache...")
            cache_key = f"route_result_{data.start_lat}_{data.start_lon}_{data.finish_lat}_{data.finish_lon}"
            await self.cache_deps.set_from_cache(cache_key, result, timeout=3600)

            logger.info(" Route calculation completed successfully.")
            return result

        except Exception as e:
            logger.error(f"Error in calculate_route: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

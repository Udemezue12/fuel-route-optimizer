# fuel_route_api/tasks.py
import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from .route_service import GeoapifyService
from .fuel_stop_service import FuelStopService
from .dependencies import CacheDependencies, CacheKeyDependencies
from .schema import RouteRequest

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@shared_task(bind=True, name="fuel_route_api.tasks.calculate_route_task")
def calculate_route_task(self, data: dict):
 
    try:
       
        data_model = RouteRequest(**data)

        
        cache_deps = CacheDependencies()
        cache_key_deps = CacheKeyDependencies()
        geoapify_service = GeoapifyService(
            cache_deps=cache_deps, cache_key_deps=cache_key_deps
        )
        fuel_service = FuelStopService(
            cache_deps=cache_deps, cache_key_deps=cache_key_deps
        )

        
        validate_coords = async_to_sync(cache_key_deps.validate_usa_coordinates)
        if not validate_coords(data_model.start_lat, data_model.start_lon):
            raise ValueError("Invalid start coordinates (not within USA bounds).")
        if not validate_coords(data_model.finish_lat, data_model.finish_lon):
            raise ValueError("Invalid finish coordinates (not within USA bounds).")

      
        get_route = async_to_sync(geoapify_service.get_geoapify_route)
        route_data = get_route(data_model, mapbox_format=False)

        route_points = [
            {"latitude": p["latitude"], "longitude": p["longitude"]}
            for p in route_data["routes"][0]["points"]
        ]
        total_distance_miles = route_data["routes"][0]["summary"]["lengthInMeters"] / 1609.34

        find_stops = async_to_sync(fuel_service.find_optimal_fuel_stops)
        fuel_stops = find_stops(route_points)

       
        calc_cost = async_to_sync(fuel_service.calculate_fuel_cost)
        total_fuel_cost = calc_cost(total_distance_miles, fuel_stops)

        calc_summary = async_to_sync(fuel_service.calculate_fuel_costs)
        cost_summary = calc_summary(total_distance_miles, fuel_stops)

     
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

     
        logger.info(" Route Calculation Complete!")
        logger.info(f"Start: ({data_model.start_lat}, {data_model.start_lon}) -> "
                    f"Finish: ({data_model.finish_lat}, {data_model.finish_lon})")
        logger.info(f"Total Distance (miles): {round(total_distance_miles, 2)}")
        logger.info(f"Route Points: {route_points}")
        logger.info(f"Fuel Stops: {fuel_stops}")
        logger.info(f"Total Fuel Cost: ${total_fuel_cost:.2f}")
        logger.info(f"Number of Stops: {cost_summary['number_of_stops']}")
        logger.info(f"Average Price per Gallon: ${cost_summary['average_price']:.2f}")
        logger.info(f"Gallons Needed: {cost_summary['gallons_needed']:.2f}")

       
        cache_key = async_to_sync(cache_key_deps.generate_cache_key)(data_model.dict())
        async_to_sync(cache_deps.set_from_cache)(cache_key, result, timeout=3600)
        logger.info(f"Cached result under key: {cache_key}")

        return {"cache_key": cache_key, "status": "done"}

    except Exception as e:
        logger.error(f" Error in calculate_route_task: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

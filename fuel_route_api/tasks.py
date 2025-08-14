import asyncio
import logging
from celery import Task, shared_task

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class CalculateRouteTask(Task):
    name = "fuel_route_api.tasks.calculate_route_task"

    def _setup_services(self):
        logger.info("🔧 Setting up service dependencies...")
        from fuel_route_api.route_service import GeoapifyService
        from fuel_route_api.fuel_stop_service import FuelStopService
        from fuel_route_api.dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies

        self.cache_deps = CacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.crud_deps = CRUDDependencies()
        self.geoapify_service = GeoapifyService(
            cache_deps=self.cache_deps,
            cache_key_deps=self.cache_key_deps
        )
        self.fuel_service = FuelStopService(
            self.cache_deps,
            self.cache_key_deps
        )
        logger.info("✅ Services initialized successfully.")

    def run(self, start_lat, start_lon, finish_lat, finish_lon, **kwargs):
        """
        Sync entrypoint for Celery worker. This wraps the async function in asyncio.run()
        so that we always have a clean event loop for each task execution.
        """
        logger.info(
            f"🚀 Task started with coordinates: start=({start_lat}, {start_lon}), finish=({finish_lat}, {finish_lon})"
        )

        self._setup_services()

        try:
            logger.info("▶ Running async route calculation...")
            return asyncio.run(
                self._async_run(start_lat, start_lon, finish_lat, finish_lon)
            )
        except Exception as e:
            logger.error(f"❌ Error in CalculateRouteTask: {str(e)}", exc_info=True)
            self.update_state(state='FAILURE', meta={
                'error': str(e),
                'exc_type': type(e).__name__
            })
            raise

    async def _async_run(self, start_lat, start_lon, finish_lat, finish_lon):
        logger.info("📍 Validating coordinates...")

        coords = type("Coord", (), {
            "start_lat": start_lat,
            "start_lon": start_lon,
            "finish_lat": finish_lat,
            "finish_lon": finish_lon
        })()

        # Validate USA coordinates
        if not await self.cache_key_deps.validate_usa_coordinates(coords.start_lat, coords.start_lon):
            raise ValueError("Invalid start coordinates (not within USA bounds).")
        if not await self.cache_key_deps.validate_usa_coordinates(coords.finish_lat, coords.finish_lon):
            raise ValueError("Invalid finish coordinates (not within USA bounds).")

        logger.info("🗺 Fetching route from Geoapify API...")
        route_data = await self.geoapify_service.get_geoapify_route(coords, mapbox_format=False)
        logger.info(f"✅ Route fetched. Summary: {route_data['routes'][0]['summary']}")

        route_points = [
            {'latitude': p['latitude'], 'longitude': p['longitude']}
            for p in route_data['routes'][0]['points']
        ]
        total_distance_miles = route_data['routes'][0]['summary']['lengthInMeters'] / 1609.34
        logger.info(f"📏 Total route distance: {total_distance_miles:.2f} miles")

        logger.info("⛽ Finding optimal fuel stops...")
        fuel_stops = await self.fuel_service.find_optimal_fuel_stops(route_points)
        logger.info(f"✅ Found {len(fuel_stops)} optimal fuel stops.")

        logger.info("💰 Calculating total fuel cost...")
        total_fuel_cost = await self.fuel_service.calculate_fuel_cost(total_distance_miles, fuel_stops)
        logger.info(f"💵 Estimated total fuel cost: ${total_fuel_cost:.2f}")

        result = {
            'route': route_points,
            'fuel_stops': fuel_stops,
            'total_fuel_cost': total_fuel_cost,
            'total_distance_miles': round(total_distance_miles, 2),
            'success': True
        }

        logger.info("🗄 Saving result to cache...")
        await self.cache_deps.set_from_cache(f'task_result_{self.request.id}', result, timeout=3600)
        logger.info(f"✅ Task {self.request.id} completed successfully.")

        return result


# Example task remains simple
@shared_task(bind=True)
def example_task(self, name):
    print(f"[Task] Started for {name}")
    import time
    time.sleep(5)
    print(f"[Task] Finished for {name}")
    return f"Hello, {name}!"

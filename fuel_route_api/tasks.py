import asyncio
import logging
from celery import Task
from fuel_route_api.route_service import GeoapifyService
from fuel_route_api.fuel_stop_service import FuelStopService
from fuel_route_api.dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class CalculateRouteTask(Task):
    name = "fuel_route_api.tasks.calculate_route_task"
    _loop = None

    def _setup_services(self):
        logger.info("🔧 Setting up service dependencies...")
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
        logger.info(f"🚀 Task started with coordinates: start=({start_lat}, {start_lon}), finish=({finish_lat}, {finish_lon})")
        
        if not self._loop:
            logger.info("🔄 Creating new asyncio event loop...")
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._setup_services()
        
        logger.info("▶ Running async route calculation...")
        return self._loop.run_until_complete(
            self._async_run(start_lat, start_lon, finish_lat, finish_lon)
        )

    async def _async_run(self, start_lat, start_lon, finish_lat, finish_lon):
        try:
            logger.info("📍 Validating coordinates...")
            coords = type("Coord", (), {
                "start_lat": start_lat,
                "start_lon": start_lon,
                "finish_lat": finish_lat,
                "finish_lon": finish_lon
            })()

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

        except Exception as e:
            logger.error(f"❌ Error in task: {str(e)}", exc_info=True)
            print(f"❌ ERROR: {type(e).__name__} - {e}")
            self.update_state(state='FAILURE', meta={
                'error': str(e),
                'exc_type': type(e).__name__
            })
            raise
import asyncio
from celery import Task
from fuel_route_api.route_service import GeoapifyService
from fuel_route_api.fuel_stop_service import FuelStopService
from fuel_route_api.dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies


class CalculateRouteTask(Task):
    name = "fuel_route_api.tasks.calculate_route_task"
    _loop = None

    def _setup_services(self):
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

    def run(self, start_lat, start_lon, finish_lat, finish_lon, **kwargs):
        if not self._loop:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self._setup_services()
        return self._loop.run_until_complete(
            self._async_run(start_lat, start_lon, finish_lat, finish_lon)
        )

    async def _async_run(self, start_lat, start_lon, finish_lat, finish_lon):
        try:
           

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

            route_data = await self.geoapify_service.get_geoapify_route(coords, mapbox_format=False)
        
            route_points = [
                {'latitude': p['latitude'], 'longitude': p['longitude']}
                for p in route_data['routes'][0]['points']
            ]
            total_distance_miles = route_data['routes'][0]['summary']['lengthInMeters'] / 1609.34
          
            fuel_stops = await self.fuel_service.find_optimal_fuel_stops(route_points)
            
            total_fuel_cost = await self.fuel_service.calculate_fuel_cost(total_distance_miles, fuel_stops)
           

            result = {
                'route': route_points,
                'fuel_stops': fuel_stops, 
                'total_fuel_cost': total_fuel_cost,
                'total_distance_miles': round(total_distance_miles, 2),
                'success': True
            }

            await self.cache_deps.set_from_cache(f'task_result_{self.request.id}', result, timeout=3600)
            

            return result

        except Exception as e:
            print(f"❌ Error in task: {str(e)}")
            self.update_state(state='FAILURE', meta={
                'error': str(e),
                'exc_type': type(e).__name__
            })
            raise

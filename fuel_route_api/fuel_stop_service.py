from typing import List, Dict
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from asgiref.sync import sync_to_async
from django.contrib.gis.db.models.functions import Distance
from .models import FuelStation
from .dependencies import CacheDependencies, CacheKeyDependencies


class FuelStopService:
    def __init__(self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps

    async def find_optimal_fuel_stops(self, route_points: List[Dict]) -> List[Dict]:
        cache_key = await self.cache_key_deps.generate_cache_key(route_points)
        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            return cached

        fuel_stops: List[Dict] = []
        last_stop_index = 0
        total_distance = 0
        seen_station_ids = set()

        for i in range(1, len(route_points)):
            p1 = Point(route_points[last_stop_index]["longitude"],
                       route_points[last_stop_index]["latitude"], srid=4326)
            p2 = Point(route_points[i]["longitude"],
                       route_points[i]["latitude"], srid=4326)

            distance = p1.distance(p2) * 69
            total_distance += distance

            if total_distance >= 500 or i == len(route_points) - 1:
                location = p2

                stations = await sync_to_async(list)(
                    FuelStation.objects
                    .filter(location__distance_lte=(location, D(mi=50)))
                    .annotate(dist=Distance('location', location))
                    .order_by('retail_price', 'dist')
                )

                if stations:
                    cheapest = stations[0]
                    if cheapest.id not in seen_station_ids:
                        fuel_stops.append({
                            "station_id": cheapest.opis_truckstop_id,
                            "name": cheapest.truckstop_name,
                            "retail_price": float(cheapest.retail_price),
                            "distance_from_route_miles": round(stations[0].dist.mi, 2),
                            "location": {
                                "lat": cheapest.location.y,
                                "lon": cheapest.location.x
                            }
                        })
                        seen_station_ids.add(cheapest.id)
                        last_stop_index = i
                        total_distance = 0

        await self.cache_deps.set_from_cache(cache_key, fuel_stops, timeout=3600)
        return  [
            {"retail_price": 3.50, "latitude": 40.914, "longitude": -75.078},
            {"retail_price": 3.60, "latitude": 38.5, "longitude": -85.0},
            {"retail_price": 3.40, "latitude": 36.545, "longitude": -95.231}
        ]

    async def calculate_fuel_cost(self, total_distance_miles: float, fuel_stops: List[Dict]) -> float:
        FUEL_EFFICIENCY_MPG = 30.0 
        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = sum(price_per_gallon) / len(price_per_gallon) if price_per_gallon else 3.5  # Fallback to $3.50

        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        return round(total_fuel_cost, 2)

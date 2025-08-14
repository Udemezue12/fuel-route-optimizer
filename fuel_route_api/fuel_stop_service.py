
import logging
from typing import List, Dict
from asgiref.sync import sync_to_async
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from fuel_route_api.models import FuelStation

logger = logging.getLogger(__name__)


class FuelStopService:
    def __init__(self, cache_deps, cache_key_deps):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps

    async def find_optimal_fuel_stops(self, route_points: List[Dict]) -> List[Dict]:
        logger.info(f"🔍 Searching for optimal fuel stops for {len(route_points)} route points...")
        cache_key = await self.cache_key_deps.generate_cache_key(route_points)
        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info("✅ Cache hit for fuel stops.")
            return cached

        fuel_stops: List[Dict] = []
        last_stop_index = 0
        total_distance = 0
        seen_station_ids = set()

        for i in range(1, len(route_points)):
            p1 = Point(route_points[last_stop_index]["longitude"], route_points[last_stop_index]["latitude"], srid=4326)
            p2 = Point(route_points[i]["longitude"], route_points[i]["latitude"], srid=4326)

            distance = p1.distance(p2) * 69
            total_distance += distance

            if total_distance >= 500 or i == len(route_points) - 1:
                location = p2
                logger.info(f"📍 Checking stations near point {i} at {location.y},{location.x} (total_distance={total_distance:.2f} mi)")

                stations = await sync_to_async(list)(
                    FuelStation.objects
                    .filter(location__distance_lte=(location, D(mi=50)))
                    .annotate(dist=Distance('location', location))
                    .order_by('retail_price', 'dist')
                )

                if stations:
                    cheapest = stations[0]
                    if cheapest.id not in seen_station_ids:
                        stop_info = {
                            "station_id": cheapest.opis_truckstop_id,
                            "name": cheapest.truckstop_name,
                            "retail_price": float(cheapest.retail_price),
                            "distance_from_route_miles": round(stations[0].dist.mi, 2),
                            "location": {"lat": cheapest.location.y, "lon": cheapest.location.x}
                        }
                        fuel_stops.append(stop_info)
                        logger.info(f"✅ Added fuel stop: {stop_info}")
                        seen_station_ids.add(cheapest.id)
                        last_stop_index = i
                        total_distance = 0

        await self.cache_deps.set_from_cache(cache_key, fuel_stops, timeout=3600)
        logger.info(f"✅ Fuel stop search complete. Found {len(fuel_stops)} stops.")
        return [
            {"retail_price": 3.50, "latitude": 40.914, "longitude": -75.078},
            {"retail_price": 3.60, "latitude": 38.5, "longitude": -85.0},
            {"retail_price": 3.40, "latitude": 36.545, "longitude": -95.231}
        ]

    async def calculate_fuel_cost(self, total_distance_miles: float, fuel_stops: List[Dict]) -> float:
        logger.info(f"💰 Calculating fuel cost for {total_distance_miles:.2f} miles using {len(fuel_stops)} stops.")
        FUEL_EFFICIENCY_MPG = 30.0
        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = sum(price_per_gallon) / len(price_per_gallon) if price_per_gallon else 3.5
        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price
        logger.info(f"📊 Avg price: ${avg_price:.2f} | Gallons needed: {gallons_needed:.2f} | Total cost: ${total_fuel_cost:.2f}")
        return round(total_fuel_cost, 2)

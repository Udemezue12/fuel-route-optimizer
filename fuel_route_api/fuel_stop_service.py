from typing import Dict, List

from asgiref.sync import sync_to_async
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString, Point
from django.contrib.gis.measure import D
from django.db import DatabaseError
from injector import inject

from fuel_route_api.models import FuelStation

from .dependencies import CacheDependencies, CacheKeyDependencies
from .log import logger


class FuelStopService:
    @inject
    def __init__(
        self, cache_deps: CacheDependencies, cache_key_deps: CacheKeyDependencies
    ):
        self.cache_deps = cache_deps
        self.cache_key_deps = cache_key_deps

    async def find_current_optimal_fuel_stops(
        self, route_coords, vehicle_range_miles=500
    ):
        cache_key = await self.cache_key_deps.generate_cache_key(
            {
                "type": "current",
                "route_coords": route_coords,
                "range": vehicle_range_miles,
            }
        )

        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info(" Cache hit for current optimal stops")
            return cached
        normalized_coords = [
            (c["lon"], c["lat"]) if isinstance(c, dict) else tuple(c)
            for c in route_coords
        ]

        route_line = LineString(normalized_coords, srid=4326)

        miles_to_degrees = vehicle_range_miles / 69.0
        try:
            stations = await sync_to_async(list)(
                FuelStation.objects.filter(
                    location__distance_lte=(route_line, miles_to_degrees)
                )
                .only("truckstop_name", "city", "retail_price", "location")
                .order_by("retail_price")[:10]
            )
        except DatabaseError as e:
            logger.error(f" DB Error while fetching optimal stops: {e}")
            return []

        results = [
            {
                "name": s.truckstop_name,
                "city": s.city,
                "retail_price": float(s.retail_price),
                "lat": s.latitude,
                "lon": s.longitude,
            }
            for s in stations[:10]
        ]
        await self.cache_deps.set_from_cache(cache_key, results, timeout=1800)
        return results

    async def find_optimal_fuel_stops(self, route_points: List[Dict]) -> List[Dict]:
        logger.info(
            f"🔍 Searching for optimal fuel stops for{len(route_points)} route points..."
        )
        cache_key = await self.cache_key_deps.generate_cache_key(route_points)
        cached = await self.cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info(f" Cache hit for fuel stops: {cached} ")
            return cached

        fuel_stops: List[Dict] = []
        seen_station_ids = set()
        total_distance = 0
        last_stop_index = 0

        step = max(1, len(route_points) // 10)
        sampled_points = route_points[::step] + [route_points[-1]]
        logger.info(
            f"📍 Sampling {len(sampled_points)} points from {len(route_points)} total points"
        )

        for i, point in enumerate(sampled_points):
            if i == 0:
                continue

            p1 = Point(
                route_points[last_stop_index]["longitude"],
                route_points[last_stop_index]["latitude"],
                srid=4326,
            )
            p2 = Point(point["longitude"], point["latitude"], srid=4326)
            distance = p1.distance(p2) * 69
            total_distance += distance

            if total_distance >= 500 or i == len(sampled_points) - 1:
                location = p2
                logger.info(
                    f" Querying fuel stations near({location.y}, {location.x}), total_distance={total_distance:.2f} mi"
                )

                try:
                    stations = await sync_to_async(list)(
                        FuelStation.objects.filter(
                            location__distance_lte=(location, D(mi=50))
                        )
                        .only(
                            "opis_truckstop_id",
                            "truckstop_name",
                            "retail_price",
                            "location",
                        )
                        .annotate(dist=Distance("location", location))
                        .order_by("retail_price", "dist")[:1]
                    )
                except DatabaseError as e:
                    logger.error(f" Database query failed: {str(e)}", exc_info=True)
                    continue

                if stations:
                    cheapest = stations[0]
                    if cheapest.id not in seen_station_ids:
                        stop_info = {
                            "station_id": cheapest.opis_truckstop_id,
                            "name": cheapest.truckstop_name,
                            "retail_price": float(cheapest.retail_price),
                            "distance_from_route_miles": round(cheapest.dist.mi, 2),
                            "location": {
                                "lat": cheapest.location.y,
                                "lon": cheapest.location.x,
                            },
                        }
                        fuel_stops.append(stop_info)
                        logger.info(f"Added fuel stop: {stop_info}")
                        seen_station_ids.add(cheapest.id)
                        last_stop_index = (
                            route_points.index(point)
                            if point in route_points
                            else last_stop_index
                        )
                        total_distance = 0
                        if len(fuel_stops) >= 3:
                            break
                else:
                    logger.warning(
                        f"No fuel stations found near ({location.y}, {location.x})"
                    )

        try:
            await self.cache_deps.set_from_cache(cache_key, fuel_stops, timeout=3600)
            logger.info(f"Cached {len(fuel_stops)} fuel  stops for key {cache_key}")
        except Exception as e:
            logger.error(f" Failed to cache fuel stops: {str(e)}", exc_info=True)

        logger.info(
            f"Fuel stop search complete. Found {len(fuel_stops)} stops: {fuel_stops}"
        )
        return fuel_stops

    async def calculate_fuel_cost(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> float:
        logger.info(
            f"Calculating fuel cost for {total_distance_miles:.2f} miles using {len(fuel_stops)} stops."
        )
        FUEL_EFFICIENCY_MPG = 30.0
        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = (
            sum(price_per_gallon) / len(price_per_gallon) if price_per_gallon else 3.5
        )
        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price
        logger.info(
            f"Avg price: ${avg_price:.2f} | Gallons needed: {gallons_needed:.2f} | Total cost: ${total_fuel_cost:.2f}"
        )
        return round(total_fuel_cost, 2)

    async def calculate_fuel_costs(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> Dict:
        logger.info(
            f"Calculating fuel cost for {total_distance_miles:.2f} miles using {len(fuel_stops)} stops."
        )

        FUEL_EFFICIENCY_MPG = 30.0
        price_per_gallon = [s["retail_price"] for s in fuel_stops]

        avg_price = (
            sum(price_per_gallon) / len(price_per_gallon) if price_per_gallon else 3.5
        )
        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        logger.info(
            f" Avg price: ${avg_price:.2f} | Gallons needed: {gallons_needed:.2f} | Total cost: ${total_fuel_cost:.2f}"
        )

        return {
            "number_of_stops": len(fuel_stops),
            "average_price": round(avg_price, 2),
            "gallons_needed": round(gallons_needed, 2),
            "total_cost": round(total_fuel_cost, 2),
        }

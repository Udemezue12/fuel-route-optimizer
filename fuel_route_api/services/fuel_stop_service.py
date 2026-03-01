from typing import Dict, List

from asgiref.sync import sync_to_async
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString, Point
from django.contrib.gis.measure import D
from django.db import DatabaseError
from injector import inject

from fuel_route_api.core.cache_dependencies import (AsyncCacheDependencies,
                                                    CacheKeyDependencies,
                                                    SyncCacheDependencies)
from fuel_route_api.core.log import logger
from fuel_route_api.models.models import FuelStation


class FuelStopService:
    @inject
    def __init__(
        self
    ):
        self.cache_deps = AsyncCacheDependencies()
        self.cache_key_deps = CacheKeyDependencies()
        self.sync_cache_deps = SyncCacheDependencies()

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

                try:
                    def get_stations():
                        return list(
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
                    stations = await sync_to_async(get_stations)()
                except DatabaseError as e:
                    logger.error(
                        f" Database query failed: {str(e)}", exc_info=True)
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

        except Exception:
            raise

        return fuel_stops

    async def calculate_fuel_cost(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> float:

        FUEL_EFFICIENCY_MPG = 30.0
        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = (
            sum(price_per_gallon) /
            len(price_per_gallon) if price_per_gallon else 3.5
        )
        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        return round(total_fuel_cost, 2)

    async def calculate_fuel_costs(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> Dict:

        FUEL_EFFICIENCY_MPG = 30.0
        price_per_gallon = [s["retail_price"] for s in fuel_stops]

        avg_price = (
            sum(price_per_gallon) /
            len(price_per_gallon) if price_per_gallon else 3.5
        )
        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        return {
            "number_of_stops": len(fuel_stops),
            "average_price": round(avg_price, 2),
            "gallons_needed": round(gallons_needed, 2),
            "total_cost": round(total_fuel_cost, 2),
        }

    def sync_find_current_optimal_fuel_stops(
        self, route_coords, vehicle_range_miles=500
    ):
        cache_key = self.cache_key_deps.sync_generate_cache_key(
            {
                "type": "current",
                "route_coords": route_coords,
                "range": vehicle_range_miles,
            }
        )

        cached = self.sync_cache_deps.get_from_cache(cache_key)
        if cached:
            logger.info("Cache hit for current optimal stops")
            return cached

        normalized_coords = [
            (c["lon"], c["lat"]) if isinstance(c, dict) else tuple(c)
            for c in route_coords
        ]

        route_line = LineString(normalized_coords, srid=4326)
        miles_to_degrees = vehicle_range_miles / 69.0

        try:
            stations = list(
                FuelStation.objects.filter(
                    location__distance_lte=(route_line, miles_to_degrees)
                )
                .only("truckstop_name", "city", "retail_price", "location")
                .order_by("retail_price")[:10]
            )
        except DatabaseError as e:
            logger.error(f"DB Error while fetching optimal stops: {e}")
            return []

        results = [
            {
                "name": s.truckstop_name,
                "city": s.city,
                "retail_price": float(s.retail_price),
                "lat": s.latitude,
                "lon": s.longitude,
            }
            for s in stations
        ]

        self.sync_cache_deps.set_from_cache(cache_key, results, timeout=1800)
        return results

    def sync_find_optimal_fuel_stops(self, route_points: List[Dict]) -> List[Dict]:

        cache_key = self.cache_key_deps.sync_generate_cache_key(route_points)
        cached = self.sync_cache_deps.get_from_cache(cache_key)

        if cached:
            logger.info(f"Cache hit for fuel stops: {cached}")
            return cached

        fuel_stops: List[Dict] = []
        seen_station_ids = set()
        total_distance = 0
        last_stop_index = 0

        step = max(1, len(route_points) // 10)
        sampled_points = route_points[::step] + [route_points[-1]]

        for i, point in enumerate(sampled_points):
            if i == 0:
                continue

            p1 = Point(
                route_points[last_stop_index]["longitude"],
                route_points[last_stop_index]["latitude"],
                srid=4326,
            )
            p2 = Point(
                point["longitude"],
                point["latitude"],
                srid=4326,
            )

            distance = p1.distance(p2) * 69
            total_distance += distance

            if total_distance >= 500 or i == len(sampled_points) - 1:
                location = p2

                try:
                    stations = list(
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
                    logger.error(
                        f"Database query failed: {str(e)}", exc_info=True
                    )
                    continue

                if stations:
                    cheapest = stations[0]

                    if cheapest.id not in seen_station_ids:
                        stop_info = {
                            "station_id": cheapest.opis_truckstop_id,
                            "name": cheapest.truckstop_name,
                            "retail_price": float(cheapest.retail_price),
                            "distance_from_route_miles": round(
                                cheapest.dist.mi, 2
                            ),
                            "location": {
                                "lat": cheapest.location.y,
                                "lon": cheapest.location.x,
                            },
                        }

                        fuel_stops.append(stop_info)
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

        self.sync_cache_deps.set_from_cache(
            cache_key, fuel_stops, timeout=3600)
        return fuel_stops

    def sync_calculate_fuel_cost(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> float:

        FUEL_EFFICIENCY_MPG = 30.0

        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = (
            sum(price_per_gallon) / len(price_per_gallon)
            if price_per_gallon
            else 3.5
        )

        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        return round(total_fuel_cost, 2)

    def sync_calculate_fuel_costs(
        self, total_distance_miles: float, fuel_stops: List[Dict]
    ) -> Dict:

        FUEL_EFFICIENCY_MPG = 30.0

        price_per_gallon = [s["retail_price"] for s in fuel_stops]
        avg_price = (
            sum(price_per_gallon) / len(price_per_gallon)
            if price_per_gallon
            else 3.5
        )

        gallons_needed = total_distance_miles / FUEL_EFFICIENCY_MPG
        total_fuel_cost = gallons_needed * avg_price

        return {
            "number_of_stops": len(fuel_stops),
            "average_price": round(avg_price, 2),
            "gallons_needed": round(gallons_needed, 2),
            "total_cost": round(total_fuel_cost, 2),
        }

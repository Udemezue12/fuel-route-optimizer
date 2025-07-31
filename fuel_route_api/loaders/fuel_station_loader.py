
from django.contrib.gis.geos import Point
from django.core.cache import cache
from asgiref.sync import sync_to_async
import pandas as pd
import os
import re
from fuel_route_api.models import FuelStation
from fuel_route_api.schema import GeocodeInputSchema
from fuel_route_api.route_service import TomTomService
from fuel_route_api.dependencies import CacheDependencies, CacheKeyDependencies, CRUDDependencies


class FuelStationLoader:
    def __init__(self, csv_path='fuel_route_api/fuel_prices.csv', marker_path='fuel_station_loaded.marker'):
        self.csv_path = csv_path
        self.marker_path = marker_path
        self.route_service = TomTomService(
            cache_deps=CacheDependencies(),
            cache_key_deps=CacheKeyDependencies(),
            deps=CRUDDependencies()
        )

    def clean_address(self, address: str) -> str:
        if not address:
            return ""
        address = re.sub(r'EXIT\s*\d+', '', address, flags=re.IGNORECASE)
        address = address.replace('&', 'and').replace(',', '')
        return address.strip()

    def is_already_loaded(self):
        return os.path.exists(self.marker_path)

    def mark_as_loaded(self):
        with open(self.marker_path, "w") as f:
            f.write("loaded")

    async def geocode_and_save(self, row):
        cleaned_address = self.clean_address(row['Address'])
        geocode_input = GeocodeInputSchema(
            address=cleaned_address,
            city=row['City'],
            state=row['State']
        )
        try:
            result = await self.route_service.geocode_address(geocode_input)
        except Exception:
            geocode_input.address = ""
            result = await self.route_service.geocode_address(geocode_input)

        location = Point(float(result.lon), float(result.lat))
        await sync_to_async(FuelStation.objects.update_or_create)(
            opis_truckstop_id=row['OPIS Truckstop ID'],
            defaults={
                'truckstop_name': row['Truckstop Name'],
                'address': row['Address'],
                'city': row['City'],
                'state': row['State'],
                'rack_id': row['Rack ID'],
                'retail_price': row['Retail Price'],
                'location': location
            }
        )

    async def async_load(self):
        if self.is_already_loaded():
            return "Fuel stations already loaded. Skipping..."

        if cache.get("fuel_stations_loading"):
            return "Load already in progress"

        cache.set("fuel_stations_loading", True, timeout=300)
        try:

            df = pd.read_csv(self.csv_path, nrows=320)

            for _, row in df.iterrows():
                await self.geocode_and_save(row)

            self.mark_as_loaded()
            return "Fuel stations loaded"
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            cache.delete("fuel_stations_loading")

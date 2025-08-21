from .models import FuelStation
from .schema import CalculateFuelStop, CalculateFuelStopLocation


def fuelstation_to_pydantic(
    fs: FuelStation, distance_from_route_miles: float
) -> CalculateFuelStop:
    return CalculateFuelStop(
        station_id=fs.opis_truckstop_id,
        name=fs.truckstop_name,
        retail_price=float(fs.retail_price),
        distance_from_route_miles=distance_from_route_miles,
        location=CalculateFuelStopLocation(lat=fs.latitude, lon=fs.longitude),
    )

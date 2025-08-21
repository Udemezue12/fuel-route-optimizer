from fuel_route_api.models import FuelStation
from fuel_route_api.schema import FuelStop


def serialize_station(station: FuelStation) -> FuelStop:
    return FuelStop(
        opis_truckstop_id=station.opis_truckstop_id,
        truckstop_name=station.truckstop_name,
        address=station.address,
        city=station.city,
        state=station.state,
        rack_id=station.rack_id,
        retail_price=float(station.retail_price),
        latitude=station.location.y,
        longitude=station.location.x,
    )

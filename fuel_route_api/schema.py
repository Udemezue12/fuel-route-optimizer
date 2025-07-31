from decimal import Decimal
from ninja import Schema
from typing import Annotated, Optional, Dict, List, Any
from pydantic import EmailStr, constr, field_validator, Field


class UserIn(Schema):
    username: Annotated[str, constr(min_length=4, max_length=20)]
    first_name: Annotated[str, constr(min_length=4, max_length=20)]
    last_name: Annotated[str, constr(min_length=4, max_length=20)]
    password: Annotated[str, constr(min_length=6)]
    email: EmailStr

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        if not v.replace(" ", "").isalpha():
            raise ValueError("Name must only contain letters and spaces")
        return v


class UserOut(Schema):
    id: Optional[int] = None
    username: str
    last_name: str
    first_name: str
    email: Optional[EmailStr] = None

    class Config:
        from_attributes = True


class LoginSchema(Schema):

    username: str
    password: str

    class Config:
        from_attributes = True


class CsrfTokenSchema(Schema):
    csrf_token: str


class LocationInput(Schema):
    latitude: float
    longitude: float
class Location(Schema):
    latitude: float
    longitude: float


class RouteInput(Schema):
    start: LocationInput
    finish: LocationInput


class FuelStop(Schema):
    opis_truckstop_id: str
    truckstop_name: str
    address: str
    city: str
    state: str
    rack_id: str
    retail_price: float
    latitude: float
    longitude: float

    class Config:
        from_attributes = True



class RouteOutput(Schema):
    route: List[Dict[str, float]]
    fuel_stops: List[FuelStop]
    total_fuel_cost: float
    total_distance_miles: float

    class Config:
        from_attributes = True


class TaskResponse(Schema):
    task_id: str
    status: str

    class Config:
        from_attributes = True


class TaskResultResponse(Schema):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class RouteRequestSchema(Schema):
    start_lat: float
    start_lon: float
    finish_lat: float
    finish_lon: float


class CoordinateSchema(Schema):
    start_lat: float = Field(..., description="Start latitude")
    start_lon: float = Field(..., description="Start longitude")
    finish_lat: float = Field(..., description="Finish latitude")
    finish_lon: float = Field(..., description="Finish longitude")


class GeocodeInputSchema(Schema):
    address: str
    city: str
    state: str


class GeocodeOutputSchema(Schema):
    lat: float
    lon: float


class RouteSchema(Schema):
    start_lat: float
    start_lon: float
    finish_lat: float
    finish_lon: float


class MapboxRouteRequestSchema(Schema):
    start_lat: float
    start_lon: float
    finish_lat: float
    finish_lon: float
class MapboxGeometry(Schema):
    coordinates: List[List[float]] = Field(
        ..., 
        example=[[-74.00597, 40.71427], [-73.935242, 40.73061]]
    )
    type: str = Field("LineString", example="LineString")


class MapboxRoute(Schema):
    geometry: MapboxGeometry
    distance: float = Field(..., example=12000)
    duration: float = Field(..., example=900)
    fuelConsumptionInLiters: float = Field(..., example=1.2)


class MapboxRouteResponseSchema(Schema):
    routes: List[MapboxRoute]



class MapboxGeocodeRequestSchema(Schema):
    address: str
    city: str
    state: str


class MapboxGeocodeResponseSchema(Schema):
    lat: float
    lon: float

class AvaliableRouteSchema(Schema):
    opis_truckstop_id : int
    truckstop_name :str
    address :str
    city :str
    state :str
    rack_id : int
    retail_price : Decimal
    latitude : float
    longitude : float

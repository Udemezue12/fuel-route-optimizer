import re
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional

from ninja import Schema
from pydantic import (
    EmailStr,
    Field,
    ValidationInfo,
    constr,
    field_validator,
    model_validator,
)
import phonenumbers

class UserIn(Schema):
    username: Annotated[str, constr(min_length=4, max_length=20)]
    first_name: Annotated[str, constr(min_length=4, max_length=20)]
    last_name: Annotated[str, constr(min_length=4, max_length=20)]
    password: Annotated[str, constr(min_length=6)]
    confirm_password: Annotated[str, constr(min_length=6)]
    email: EmailStr
    phone_number:str
    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str):
        try:
            parsed = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number. Use full international format.")
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
        except Exception:
            raise ValueError("Invalid phone number format. Use e.g. +2348012345678")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v):
        if not v.replace(" ", "").isalpha():
            raise ValueError("Name must only contain letters and spaces")
        return v
    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v, info: ValidationInfo):
        password = info.data.get("password")

        if password and v != password:
            raise ValueError("Passwords do not match")

        return v
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        errors = []
        if len(v) < 7:
            errors.append("≥7 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("lowercase letter")
        if not re.search(r"\d", v):
            errors.append("number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("special character")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors))
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

class VerifyEmail(Schema):
    otp: Optional[str] = None
    token: Optional[str] = None
    @model_validator(mode="before")
    @classmethod
    def validate_token_or_otp(cls, values):
        token = values.get("token")
        otp = values.get("otp")
        if not token and not otp:
            raise ValueError("Either token or otp must be provided")
        return values
class ForgotPasswordSchema(Schema):
    email: EmailStr


class ResetPasswordSchema(Schema):
    token: Optional[str] = None
    otp: Optional[str] = None
    new_password: str

    @model_validator(mode="before")
    @classmethod
    def validate_token_or_otp(cls, values):
        token = values.get("token")
        otp = values.get("otp")
        if not token and not otp:
            raise ValueError("Either token or otp must be provided")
        return values
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
        ..., example=[[-74.00597, 40.71427], [-73.935242, 40.73061]]
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
    opis_truckstop_id: int
    truckstop_name: str
    address: str
    city: str
    state: str
    rack_id: int
    retail_price: Decimal
    latitude: float
    longitude: float


class RouteRequest(Schema):
    start_lat: float
    start_lon: float
    finish_lat: float
    finish_lon: float


class CalculateRoutePoint(Schema):
    latitude: float
    longitude: float


class CalculateFuelStopLocation(Schema):
    lat: float
    lon: float


class CalculateFuelStop(Schema):
    station_id: str
    name: str
    retail_price: float
    distance_from_route_miles: float
    location: CalculateFuelStopLocation


class RouteResponse(Schema):
    route: List[CalculateRoutePoint]
    fuel_stops: List[CalculateFuelStop]
    total_fuel_cost: float
    total_distance_miles: float
    number_of_stops: int
    average_price: float | None = None
    gallons_needed: float | None = None
    success: bool


class ErrorResponse(Schema):
    success: bool
    error: str

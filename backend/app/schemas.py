from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class GreetingOut(BaseModel):
    text: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str

    model_config = {"from_attributes": True}


class LocationOut(BaseModel):
    id: int
    name: str
    address: str
    description: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class ReservationOut(BaseModel):
    id: int
    guest_name: str
    check_in: date
    check_out: date

    model_config = {"from_attributes": True}


class RoomOut(BaseModel):
    id: int
    name: str
    capacity: int
    price_per_night: float
    amenities: str
    current_reservation: ReservationOut | None = None

    model_config = {"from_attributes": True}


class ReservationDetailOut(BaseModel):
    id: int
    guest_name: str
    check_in: date
    check_out: date
    room_id: int
    room_name: str
    location_id: int
    location_name: str
    assistant_id: int | None = None
    assistant_name: str | None = None


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    capacity: int = Field(ge=1, le=20)
    price_per_night: float = Field(ge=0)
    amenities: str = Field(default="", max_length=500)


class LocationDetailOut(LocationOut):
    rooms: list[RoomOut]


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=500)
    latitude: float = Field(default=52.2297, ge=-90, le=90)
    longitude: float = Field(default=21.0122, ge=-180, le=180)


class AssistantOut(BaseModel):
    id: int
    name: str
    status: str
    voice: str
    traits: str
    max_concurrent_calls: int
    minutes_used: int
    locations: list[LocationOut]

    model_config = {"from_attributes": True}


class AssistantUpdate(BaseModel):
    status: Literal["active", "offline"] | None = None
    voice: str | None = Field(default=None, min_length=1, max_length=255)
    traits: str | None = Field(default=None, max_length=2000)
    max_concurrent_calls: int | None = Field(default=None, ge=1, le=20)
    location_ids: list[int] | None = None


class UsageOut(BaseModel):
    minutes_used: int
    minutes_included: int

    model_config = {"from_attributes": True}

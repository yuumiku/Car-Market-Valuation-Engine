from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_serializer, field_validator


class FuelType(str, Enum):
    PETROL = "Petrol"
    DIESEL = "Diesel"
    GASOLINE = "Gasoline"
    HYBRID = "Hybrid"
    ELECTRIC = "Electric"
    GPL = "GPL"
    UNKNOWN = "Unknown"


class GearboxType(str, Enum):
    MANUAL = "Manual"
    AUTOMATIC = "Automatic"
    SEMI_AUTOMATIC = "Semi-Automatic"
    ELECTRIC = "Electric"
    UNKNOWN = "Unknown"


class SellerType(str, Enum):
    PRIVATE = "Private"
    DEALER = "Dealer"
    UNKNOWN = "Unknown"


class Source(str, Enum):
    AUTOMOBILE_TN = "Automobile_tn"
    TAYARA_TN = "Tayara_tn"
    BANIOULA_TN = "Banioula_tn"
    FACEBOOK = "Facebook"


class CarStatus(str, Enum):
    GREAT = "Great"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    UNKNOWN = "Unknown"


TUNISIAN_REGIONS = {
    "ariana",
    "beja",
    "ben arous",
    "bizerte",
    "gabes",
    "gafsa",
    "jendouba",
    "kairouan",
    "kasserine",
    "kebili",
    "kef",
    "mahdia",
    "manouba",
    "medenine",
    "monastir",
    "nabeul",
    "sfax",
    "sidi bouzid",
    "siliana",
    "sousse",
    "tataouine",
    "tozeur",
    "tunis",
    "zaghouan",
}


class ListingItem(BaseModel):
    listing_id: str = Field(..., description="Unique identifier for the listing")
    source: str = Field(..., description="Source of the listing")
    url: str = Field(..., description="URL of the listing")

    title: str | None = Field(None, description="Title of the listing")
    make: str = Field(..., description="Make of the car / car brand")
    model: str = Field(..., description="Model of the car")
    generation: str | None = Field(None, description="Car generation or version")
    engine: str | None = Field(None, description="Car's engine name")
    cylinder_capacity: int | None = Field(
        None, ge=1, le=8000, description="Cylinder capacity in cm3"
    )
    year: int | None = Field(
        None, ge=1970, le=datetime.now(tz=datetime.timezone.utc).year + 1
    )
    mileage_km: int | None = Field(None, ge=0, le=2_000_000)
    fuel_type: FuelType = FuelType.UNKNOWN
    gearbox_type: GearboxType = GearboxType.UNKNOWN
    color: str | None = None
    doors: int | None = Field(None, ge=1, le=7, description="Number of doors")
    places: int | None = Field(None, ge=1, le=9, description="Number of seats")
    fiscal_power: int | None = Field(
        None, ge=1, le=200, description="Fiscal power of the car"
    )

    usage_status: str | None = None
    global_status: CarStatus = CarStatus.UNKNOWN

    price_tnd: float | None = Field(None, ge=0)
    price_raw: str | None = None
    negotiable: bool = False

    region: str | None = None
    city: str | None = None

    seller_type: SellerType = SellerType.UNKNOWN
    seller_name: str | None = None
    seller_phone: str | None = None
    seller_address: str | None = None

    image_urls: list[str] = Field(default_factory=list)

    posted_at: datetime | None = None
    scraped_at: datetime = Field(default_factory=datetime.now)

    @field_validator("make", "model", mode="before")
    @classmethod
    def strip_and_title(cls, v: str) -> str:
        return v.strip().title() if isinstance(v, str) else v

    @field_validator("region", mode="before")
    def normalize_region(cls, v: str | None) -> str | None:
        if v is None:
            return v
        normalized = v.strip().lower()
        if normalized in TUNISIAN_REGIONS:
            return normalized.title()
        return v.strip().title()

    @field_validator("price_raw", mode="before")
    @classmethod
    def parse_price(cls, v) -> str | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, str):
            cleaned = (
                v.replace(" ", "")
                .replace(",", ".")
                .replace("DT", "")
                .replace("TND", "")
                .strip()
            )
            return cleaned if cleaned else None
        return None

    @field_validator("mileage_km", mode="before")
    @classmethod
    def parse_mileage(cls, v) -> int | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            cleaned = (
                v.replace(" ", "")
                .replace(",", ".")
                .replace("KM", "")
                .replace("km", "")
                .strip()
            )
            try:
                return int(float(cleaned))
            except ValueError:
                return None
        return None

    @field_serializer("posted_at", "scraped_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime as ISO format string."""
        if value is None:
            return None
        return value.isoformat()

    class Config:
        use_enum_values = True

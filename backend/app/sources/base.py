"""Базовий інтерфейс джерела даних. Кожне джерело — окремий модуль."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Callable


@dataclass
class SearchArea:
    label: str
    lat: float
    lon: float
    radius_m: int | None = None  # якщо задано — пошук по колу
    osm_area_id: int | None = None  # інакше — в межах адміністративної території
    bbox: tuple[float, float, float, float] | None = None  # south, west, north, east
    city: str | None = None
    region: str | None = None
    country: str | None = None
    country_code: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SearchArea":
        d = dict(d)
        if d.get("bbox"):
            d["bbox"] = tuple(d["bbox"])
        return cls(**d)


@dataclass
class RawBusiness:
    source: str
    source_id: str
    name: str
    category: str = "other"
    raw_type: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    postcode: str | None = None
    lat: float | None = None
    lon: float | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    socials: dict = field(default_factory=dict)
    map_url: str | None = None
    source_url: str | None = None
    opening_hours: str | None = None
    brand: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    menu_url: str | None = None
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RawBusiness":
        return cls(**d)


LogFn = Callable[[str, str], None]  # (level, message)


class BaseSource(ABC):
    key: str = "base"
    label: str = "Base"
    requires_key: bool = False
    description: str = ""
    key_help: str = ""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @abstractmethod
    def search(self, area: SearchArea, categories: list[str], limit: int, log: LogFn) -> list[RawBusiness]:
        """Повертає список знайдених бізнесів (без аналізу)."""

    def is_available(self) -> bool:
        return not self.requires_key or bool(self.api_key)

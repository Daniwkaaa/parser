"""Схеми запитів API та серіалізація."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .analysis.evaluate import PROBLEM_LABELS
from .categories import CATEGORY_MAP, category_label
from .models import CLIENT_STATUSES, Business
from .sources.registry import SOURCES


class SearchRequest(BaseModel):
    scope: Literal["city", "oblast", "country"] = "city"
    country: str | None = "Україна"
    region: str | None = None
    city: str | None = None
    district: str | None = None
    radius_km: float | None = Field(default=None, ge=0, le=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    categories: list[str] = Field(min_length=1)
    limit: int = Field(default=100, ge=1, le=5000)
    problems: list[str] = []
    comprehensive: bool = True
    sources: list[str] = ["osm"]
    check_websites: bool = True
    exclude_chains: bool = True

    @field_validator("categories")
    @classmethod
    def _cats(cls, v):
        bad = [c for c in v if c not in CATEGORY_MAP]
        if bad:
            raise ValueError(f"Невідомі категорії: {bad}")
        return v

    @field_validator("problems")
    @classmethod
    def _probs(cls, v):
        bad = [p for p in v if p not in PROBLEM_LABELS]
        if bad:
            raise ValueError(f"Невідомі типи проблем: {bad}")
        return v

    @field_validator("sources")
    @classmethod
    def _srcs(cls, v):
        bad = [s for s in v if s not in SOURCES]
        if bad:
            raise ValueError(f"Невідомі джерела: {bad}")
        return v or ["osm"]

    @field_validator("country", "region", "city", "district")
    @classmethod
    def _strip(cls, v):
        return v.strip() or None if isinstance(v, str) else v


class GeocodeRequest(BaseModel):
    country: str | None = None
    region: str | None = None
    city: str | None = None
    district: str | None = None
    radius_km: float | None = None


class BusinessUpdate(BaseModel):
    status: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    address: str | None = None

    @field_validator("status")
    @classmethod
    def _st(cls, v):
        if v is not None and v not in CLIENT_STATUSES:
            raise ValueError("Невідомий статус")
        return v


class NoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class ApiKeysUpdate(BaseModel):
    google_places: str | None = None
    serpapi: str | None = None


class ScoringUpdate(BaseModel):
    weights: dict[str, int]
    thresholds: dict[Literal["high", "medium"], int]


def business_brief(b: Business) -> dict:
    return {
        "id": b.id, "name": b.name, "category": b.category, "category_label": category_label(b.category),
        "address": b.address, "city": b.city, "phone": b.phone, "email": b.email, "website": b.website,
        "instagram": b.instagram, "facebook": b.facebook, "lat": b.lat, "lon": b.lon,
        "website_status": b.website_status, "menu_status": b.menu_status, "booking_status": b.booking_status,
        "outdated_status": b.outdated_status, "problems": b.problems or [], "lead_score": b.lead_score,
        "lead_tier": b.lead_tier, "status": b.status, "contact_verified": b.contact_verified,
        "rating": b.rating, "reviews_count": b.reviews_count,
        "sources": [s.get("source") for s in (b.sources or [])],
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "last_checked_at": b.last_checked_at.isoformat() if b.last_checked_at else None,
    }


def business_full(b: Business) -> dict:
    d = business_brief(b)
    d.update({
        "region": b.region, "country": b.country, "postcode": b.postcode, "raw_type": b.raw_type,
        "socials": b.socials or {}, "map_url": b.map_url, "opening_hours": b.opening_hours, "brand": b.brand,
        "sources_full": b.sources or [], "website_analysis": b.website_analysis or {},
        "problem_details": b.problem_details or [], "summary": b.summary, "recommendation": b.recommendation,
        "recommended_services": b.recommended_services or [], "score_breakdown": b.score_breakdown or [],
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        "notes": [{"id": n.id, "text": n.text, "created_at": n.created_at.isoformat()} for n in b.notes],
        "osm_tags": {k: v for k, v in (b.source_tags or {}).items() if not k.startswith("_")},
    })
    return d

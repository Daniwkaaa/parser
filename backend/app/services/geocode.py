"""Геокодування через Nominatim (OSM) з кешем у БД, відповідно до правил використання (1 запит/с)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import GeocodeCache
from ..sources.base import SearchArea
from .http import HttpError, request


class GeocodeError(Exception):
    pass


def _nominatim(db: Session, params: dict) -> list[dict]:
    key = "|".join(f"{k}={v}" for k, v in sorted(params.items()))
    cached = db.get(GeocodeCache, key)
    if cached is not None:
        return cached.result.get("items", [])
    url = get_settings().nominatim_url.rstrip("/") + "/search"
    q = {**params, "format": "jsonv2", "addressdetails": 1, "limit": 5, "accept-language": "uk"}
    try:
        resp = request("GET", url, params=q, timeout=20)
    except HttpError as e:
        raise GeocodeError(f"Nominatim недоступний: {e}") from e
    if resp.status_code != 200:
        raise GeocodeError(f"Nominatim повернув HTTP {resp.status_code}")
    items = resp.json()
    db.merge(GeocodeCache(query=key, result={"items": items}))
    db.commit()
    return items


def resolve_area(db: Session, *, country: str | None, region: str | None, city: str | None,
                 district: str | None = None, radius_km: float | None = None,
                 lat: float | None = None, lon: float | None = None) -> SearchArea:
    if lat is not None and lon is not None:
        r = int((radius_km or 2) * 1000)
        return SearchArea(label=f"{lat:.5f}, {lon:.5f} (радіус {r/1000:g} км)", lat=lat, lon=lon, radius_m=r,
                          city=city, region=region, country=country)
    if not city and not region and not country:
        raise GeocodeError("Вкажіть хоча б місто, регіон або країну")

    items: list[dict] = []
    if district and city:
        items = _nominatim(db, {"q": ", ".join(p for p in [district, city, region, country] if p)})
    if not items:
        params = {}
        if city:
            params["city"] = city
        if region:
            params["state"] = region
        if country:
            params["country"] = country
        items = _nominatim(db, params)
        if not items and city:  # структурований запит не спрацював — пробуємо вільний текст
            items = _nominatim(db, {"q": ", ".join(p for p in [city, region, country] if p)})
    if not items:
        raise GeocodeError("Локацію не знайдено в OpenStreetMap. Перевірте написання назви.")

    # перевага адміністративним межам (relation)
    best = next((i for i in items if i.get("osm_type") == "relation"), items[0])
    addr = best.get("address", {})
    bb = best.get("boundingbox")
    bbox = (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3])) if bb else None
    area = SearchArea(
        label=best.get("display_name", city or region or country or ""),
        lat=float(best["lat"]), lon=float(best["lon"]), bbox=bbox,
        city=city or addr.get("city") or addr.get("town") or addr.get("village"),
        region=region or addr.get("state"), country=country or addr.get("country"),
        country_code=(addr.get("country_code") or "").upper() or None,
    )
    if radius_km and radius_km > 0:
        area.radius_m = int(radius_km * 1000)
        area.label = f"{area.label} — радіус {radius_km:g} км від центру"
    elif best.get("osm_type") == "relation":
        area.osm_area_id = 3600000000 + int(best["osm_id"])
    else:
        area.radius_m = 3000
        area.label = f"{area.label} — радіус 3 км (межі території не знайдено)"
    return area

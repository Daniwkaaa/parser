"""Джерело: Google Places API (New) — Text Search. Потрібен власний API-ключ.

Ключ: https://console.cloud.google.com/ → APIs & Services → увімкнути «Places API (New)» → Credentials → API key.
Оплата за запити згідно з тарифами Google Maps Platform.
"""
from __future__ import annotations

from ..categories import CATEGORY_MAP
from ..services.http import HttpError, request
from .base import BaseSource, LogFn, RawBusiness, SearchArea

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress", "places.location", "places.types",
    "places.nationalPhoneNumber", "places.internationalPhoneNumber", "places.websiteUri", "places.googleMapsUri",
    "places.rating", "places.userRatingCount", "places.businessStatus", "places.regularOpeningHours",
    "nextPageToken",
])


class GooglePlacesSource(BaseSource):
    key = "google_places"
    label = "Google Places API"
    requires_key = True
    description = "Офіційний API Google Maps: рейтинги, відгуки, сайти, телефони. Платний за запити."
    key_help = "Google Cloud Console → увімкніть «Places API (New)» → Credentials → Create API key."

    def search(self, area: SearchArea, categories: list[str], limit: int, log: LogFn) -> list[RawBusiness]:
        out: list[RawBusiness] = []
        per_cat = max(20, limit // max(1, len(categories)) + 20)
        radius = float(area.radius_m or 5000)
        for key in categories:
            cat = CATEGORY_MAP.get(key)
            if not cat:
                continue
            body = {
                "textQuery": f"{cat.query} {area.city or ''}".strip(),
                "languageCode": "uk",
                "pageSize": 20,
                "locationBias": {"circle": {"center": {"latitude": area.lat, "longitude": area.lon}, "radius": min(radius, 50000.0)}},
            }
            got = 0
            token = None
            for _page in range(3):  # API дає максимум 60 результатів на запит
                if token:
                    body["pageToken"] = token
                try:
                    resp = request("POST", URL, json=body, headers={"X-Goog-Api-Key": self.api_key or "", "X-Goog-FieldMask": FIELDS}, timeout=30)
                except HttpError as e:
                    log("error", f"Google Places: {e}")
                    break
                if resp.status_code != 200:
                    log("error", f"Google Places HTTP {resp.status_code}: {resp.text[:200]}")
                    break
                data = resp.json()
                for p in data.get("places", []):
                    if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                        continue
                    loc = p.get("location") or {}
                    hours = (p.get("regularOpeningHours") or {}).get("weekdayDescriptions")
                    out.append(RawBusiness(
                        source="google_places", source_id=p["id"], name=(p.get("displayName") or {}).get("text", ""),
                        category=key, raw_type=",".join(p.get("types", [])[:3]), address=p.get("formattedAddress"),
                        city=area.city, region=area.region, country=area.country,
                        lat=loc.get("latitude"), lon=loc.get("longitude"),
                        phone=p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber"),
                        website=p.get("websiteUri"), map_url=p.get("googleMapsUri"), source_url=p.get("googleMapsUri"),
                        rating=p.get("rating"), reviews_count=p.get("userRatingCount"),
                        opening_hours="; ".join(hours) if hours else None,
                    ))
                    got += 1
                token = data.get("nextPageToken")
                if not token or got >= per_cat:
                    break
            log("info", f"Google Places «{cat.label}»: {got}")
        return [b for b in out if b.name]

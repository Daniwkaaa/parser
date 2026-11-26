"""Джерело: SerpAPI (Google Maps engine). Потрібен власний API-ключ.

Ключ: https://serpapi.com/manage-api-key (є безкоштовний ліміт запитів на місяць).
"""
from __future__ import annotations

from ..categories import CATEGORY_MAP
from ..services.http import HttpError, request
from .base import BaseSource, LogFn, RawBusiness, SearchArea

URL = "https://serpapi.com/search.json"


class SerpApiSource(BaseSource):
    key = "serpapi"
    label = "SerpAPI (Google Maps)"
    requires_key = True
    description = "Результати Google Maps через офіційний API SerpAPI: рейтинги, відгуки, сайти."
    key_help = "Зареєструйтесь на serpapi.com → Dashboard → Your Private API Key."

    def search(self, area: SearchArea, categories: list[str], limit: int, log: LogFn) -> list[RawBusiness]:
        out: list[RawBusiness] = []
        per_cat = max(20, limit // max(1, len(categories)) + 10)
        zoom = 14 if (area.radius_m or 5000) <= 5000 else 12
        for key in categories:
            cat = CATEGORY_MAP.get(key)
            if not cat:
                continue
            got = 0
            for start in range(0, min(per_cat, 120), 20):
                params = {"engine": "google_maps", "type": "search", "q": cat.query, "hl": "uk",
                          "ll": f"@{area.lat},{area.lon},{zoom}z", "start": start, "api_key": self.api_key}
                try:
                    resp = request("GET", URL, params=params, timeout=60)
                except HttpError as e:
                    log("error", f"SerpAPI: {e}")
                    break
                if resp.status_code != 200:
                    log("error", f"SerpAPI HTTP {resp.status_code}: {resp.text[:200]}")
                    break
                data = resp.json()
                if data.get("error"):
                    log("error", f"SerpAPI: {data['error']}")
                    break
                results = data.get("local_results") or []
                for r in results:
                    gps = r.get("gps_coordinates") or {}
                    pid = r.get("place_id") or r.get("data_id") or r.get("title")
                    out.append(RawBusiness(
                        source="serpapi", source_id=str(pid), name=r.get("title", ""), category=key,
                        raw_type=r.get("type"), address=r.get("address"), city=area.city, region=area.region,
                        country=area.country, lat=gps.get("latitude"), lon=gps.get("longitude"), phone=r.get("phone"),
                        website=r.get("website"), rating=r.get("rating"), reviews_count=r.get("reviews"),
                        map_url=f"https://www.google.com/maps/place/?q=place_id:{r['place_id']}" if r.get("place_id") else None,
                        source_url=r.get("place_id_search"), opening_hours=(r.get("hours") or None) if isinstance(r.get("hours"), str) else None,
                    ))
                    got += 1
                if len(results) < 20:
                    break
            log("info", f"SerpAPI «{cat.label}»: {got}")
        return [b for b in out if b.name]

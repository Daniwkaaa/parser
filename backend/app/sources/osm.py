"""Джерело: OpenStreetMap через Overpass API (безкоштовно, без ключа).

Дані OSM © учасники OpenStreetMap, ліцензія ODbL.
"""
from __future__ import annotations

from ..categories import CATEGORY_MAP, classify_osm_tags
from ..config import get_settings
from ..services.http import HttpError, request
from .base import BaseSource, LogFn, RawBusiness, SearchArea

SOCIAL_TAGS = {
    "instagram": ("contact:instagram", "instagram"),
    "facebook": ("contact:facebook", "facebook"),
    "telegram": ("contact:telegram", "telegram"),
    "viber": ("contact:viber", "viber"),
    "whatsapp": ("contact:whatsapp", "whatsapp"),
    "tiktok": ("contact:tiktok", "tiktok"),
    "youtube": ("contact:youtube", "youtube"),
}


def _first(tags: dict, *keys: str) -> str | None:
    for k in keys:
        v = tags.get(k)
        if v and v.strip():
            return v.strip()
    return None


def build_query(area: SearchArea, categories: list[str], limit: int, timeout: int = 120) -> str:
    if area.radius_m:
        selector = f"(around:{int(area.radius_m)},{area.lat:.6f},{area.lon:.6f})"
        header = ""
    elif area.osm_area_id:
        selector = "(area.searchArea)"
        header = f"area({area.osm_area_id})->.searchArea;\n"
    elif area.bbox:
        s, w, n, e = area.bbox
        selector = f"({s},{w},{n},{e})"
        header = ""
    else:
        raise ValueError("Не задано територію пошуку")
    parts = []
    for key in categories:
        cat = CATEGORY_MAP.get(key)
        if not cat:
            continue
        for flt in cat.osm:
            parts.append(f'  nwr[{flt}]["name"]{selector};')
    if not parts:
        raise ValueError("Не обрано жодної категорії")
    body = "\n".join(parts)
    return f"[out:json][timeout:{timeout}];\n{header}(\n{body}\n);\nout center tags {int(limit)};"


def element_to_business(el: dict) -> RawBusiness | None:
    tags = el.get("tags") or {}
    name = (tags.get("name") or "").strip()
    if not name:
        return None
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    street = _first(tags, "addr:street", "addr:place")
    house = tags.get("addr:housenumber")
    city = _first(tags, "addr:city")
    address = ", ".join(p for p in [" ".join(p for p in [street, house] if p) or None, city] if p) or _first(tags, "addr:full")
    socials = {}
    for net, keys in SOCIAL_TAGS.items():
        v = _first(tags, *keys)
        if v:
            socials[net] = v
    osm_type, osm_id = el.get("type"), el.get("id")
    raw_type = next((f"{k}={tags[k]}" for k in ("amenity", "shop", "tourism", "craft", "office", "healthcare", "leisure") if k in tags), None)
    return RawBusiness(
        source="osm",
        source_id=f"{osm_type}/{osm_id}",
        name=name,
        category=classify_osm_tags(tags),
        raw_type=raw_type,
        address=address,
        city=city,
        postcode=tags.get("addr:postcode"),
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
        phone=_first(tags, "contact:phone", "phone", "contact:mobile", "mobile"),
        email=_first(tags, "contact:email", "email"),
        website=_first(tags, "contact:website", "website", "url"),
        instagram=socials.pop("instagram", None),
        facebook=socials.pop("facebook", None),
        socials=socials,
        map_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        source_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        opening_hours=tags.get("opening_hours"),
        brand=_first(tags, "brand", "operator:wikidata", "brand:wikidata"),
        menu_url=_first(tags, "website:menu", "menu:url", "contact:menu"),
        tags={k: v for k, v in tags.items() if not k.startswith("name:")},
    )


class OSMSource(BaseSource):
    key = "osm"
    label = "OpenStreetMap (Overpass API)"
    requires_key = False
    description = "Безкоштовне відкрите джерело. Працює без ключів. Дані © учасники OpenStreetMap (ODbL)."

    def search(self, area: SearchArea, categories: list[str], limit: int, log: LogFn) -> list[RawBusiness]:
        # беремо із запасом, бо частина відсіється (мережі, дублікати, фільтри)
        fetch = max(50, min(limit * 4, 3000))
        query = build_query(area, categories, fetch)
        data = None
        errors = []
        for url in get_settings().overpass_url_list:
            log("info", f"Запит до Overpass: {url.split('/')[2]}")
            try:
                resp = request("POST", url, data={"data": query}, timeout=180, retries=2, backoff=10)
            except HttpError as e:
                errors.append(str(e))
                log("warning", f"Сервер Overpass недоступний, пробую наступний: {e}")
                continue
            if resp.status_code != 200:
                errors.append(f"HTTP {resp.status_code}")
                log("warning", f"Overpass відповів HTTP {resp.status_code}, пробую наступний сервер")
                continue
            try:
                data = resp.json()
            except ValueError:
                errors.append("некоректний JSON")
                continue
            if data.get("remark") and "runtime error" in data["remark"]:
                log("warning", f"Overpass: {data['remark'][:200]}")
            break
        if data is None:
            raise RuntimeError("Усі сервери Overpass недоступні: " + "; ".join(errors))
        out: list[RawBusiness] = []
        seen = set()
        for el in data.get("elements", []):
            b = element_to_business(el)
            if b and b.source_id not in seen:
                seen.add(b.source_id)
                if not b.city and area.city:
                    b.city = area.city
                b.region = area.region
                b.country = area.country
                out.append(b)
        log("info", f"OpenStreetMap: отримано {len(out)} об'єктів")
        return out

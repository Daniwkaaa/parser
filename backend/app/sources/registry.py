"""Реєстр джерел. Щоб додати нове джерело — створіть модуль із класом BaseSource і додайте його сюди."""
from __future__ import annotations

from .base import BaseSource
from .google_places import GooglePlacesSource
from .osm import OSMSource
from .serpapi import SerpApiSource

SOURCES: dict[str, type[BaseSource]] = {
    OSMSource.key: OSMSource,
    GooglePlacesSource.key: GooglePlacesSource,
    SerpApiSource.key: SerpApiSource,
}


def describe() -> list[dict]:
    return [
        {"key": c.key, "label": c.label, "requires_key": c.requires_key, "description": c.description, "key_help": c.key_help}
        for c in SOURCES.values()
    ]

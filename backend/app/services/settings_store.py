"""Налаштування застосунку, що зберігаються в БД (змінювані з інтерфейсу)."""
from __future__ import annotations

import copy
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AppSetting

DEFAULTS: dict[str, Any] = {
    "scoring": {
        "weights": {
            "no_website": 30,
            "no_menu": 20,
            "social_only": 15,
            "no_booking": 10,
            "outdated_website": 15,
            "website_unreachable": 15,
            "has_contact": 10,
            "incomplete_info": 5,
            "website_improvable": 5,
        },
        "thresholds": {"high": 70, "medium": 40},
    },
    "sources": {"osm": True, "google_places": False, "serpapi": False},
    "api_keys": {"google_places": "", "serpapi": ""},
    "search": {
        "country": "Україна",
        "limit": 100,
        "radius_km": 3,
        "exclude_chains": True,
        "check_websites": True,
        "language": "uk",
    },
}

SCORING_LABELS = {
    "no_website": "Немає власного сайту",
    "no_menu": "Немає онлайн-меню / каталогу / переліку послуг",
    "social_only": "Лише соцмережі замість сайту",
    "no_booking": "Немає онлайн-запису / бронювання",
    "outdated_website": "Застарілий сайт або серйозні проблеми",
    "website_unreachable": "Сайт вказано, але він не працює",
    "has_contact": "Є публічний телефон або email",
    "incomplete_info": "Неповна інформація про бізнес",
    "website_improvable": "Сайт є, але має що покращити",
}


def _merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            out[k] = _merge(base.get(k), v) if k in base else v
        return out
    return override if override is not None else base


def get_value(db: Session, key: str) -> Any:
    row = db.get(AppSetting, key)
    default = copy.deepcopy(DEFAULTS.get(key))
    if row is None:
        return default
    return _merge(default, row.value) if default is not None else row.value


def set_value(db: Session, key: str, value: Any) -> Any:
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    return get_value(db, key)


def get_api_key(db: Session, name: str) -> str:
    keys = get_value(db, "api_keys") or {}
    val = (keys.get(name) or "").strip()
    if val:
        return val
    s = get_settings()
    return {"google_places": s.google_places_api_key, "serpapi": s.serpapi_api_key}.get(name, "") or ""


def all_settings(db: Session, mask_keys: bool = True) -> dict:
    data = {k: get_value(db, k) for k in DEFAULTS}
    keys = {}
    for name in DEFAULTS["api_keys"]:
        v = get_api_key(db, name)
        stored = (data["api_keys"].get(name) or "").strip()
        keys[name] = {
            "configured": bool(v),
            "from_env": bool(v) and not stored,
            "masked": (v[:4] + "…" + v[-4:]) if (v and len(v) > 10) else ("••••" if v else ""),
        }
    data["api_keys"] = keys if mask_keys else data["api_keys"]
    data["scoring_labels"] = SCORING_LABELS
    return data

"""Видалення дублікатів: зіставлення за ID джерела, телефоном, назвою, адресою та координатами."""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Business, SourceRef

LEGAL_FORMS = r"\b(тов|фоп|пп|ооо|ип|чп|llc|ltd|inc|gmbh|кафе|ресторан|бар|кавярня|кофейня|перукарня|піцерія|салон|магазин|готель|хостел|hotel|hostel|cafe|restaurant|coffee)\b"


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = name.lower().replace("ё", "е")
    s = re.sub(r"[\"'`’ʼ«»“”„]", "", s)
    s = re.sub(LEGAL_FORMS, " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_address(addr: str | None) -> str | None:
    if not addr:
        return None
    s = addr.lower()
    s = re.sub(r"\b(вулиця|вул|улица|ул|проспект|просп|пр-т|пр|площа|пл|провулок|пров|бульвар|бул|street|st|avenue|ave)\b\.?", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\b\d{5}\b", " ", s)  # поштовий індекс
    s = re.sub(r"\b(україна|ukraine)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip() or None


def distance_m(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def find_duplicate(db: Session, *, source: str, source_id: str, name_norm: str, phone_norm: str | None,
                   address_norm: str | None, lat: float | None, lon: float | None) -> tuple[Business | None, str | None]:
    ref = db.execute(select(SourceRef).where(SourceRef.source == source, SourceRef.source_id == source_id)).scalar_one_or_none()
    if ref:
        return db.get(Business, ref.business_id), "той самий ID у джерелі"

    conds = [Business.name_norm == name_norm]
    if phone_norm:
        conds.append(Business.phone_norm == phone_norm)
    if address_norm:
        conds.append(Business.address_norm == address_norm)
    if lat is not None and lon is not None:
        d = 0.003  # ~300 м
        conds.append((Business.lat.between(lat - d, lat + d)) & (Business.lon.between(lon - d * 1.6, lon + d * 1.6)))
    cands = db.execute(select(Business).where(or_(*conds)).limit(200)).scalars().all()

    best, reason, best_score = None, None, 0.0
    for c in cands:
        sim = similar(name_norm, c.name_norm)
        dist = distance_m(lat, lon, c.lat, c.lon)
        score, why = 0.0, None
        if phone_norm and c.phone_norm == phone_norm and (sim >= 0.6 or dist < 200):
            score, why = 0.95, "збіг телефону"
        elif sim >= 0.92 and dist < 150:
            score, why = 0.9, "збіг назви та розташування"
        elif sim >= 0.92 and address_norm and c.address_norm == address_norm:
            score, why = 0.9, "збіг назви та адреси"
        elif sim >= 0.8 and dist < 40:
            score, why = 0.8, "схожа назва за тією самою адресою"
        if score > best_score:
            best, reason, best_score = c, why, score
    return best, reason


def add_source_ref(db: Session, business_id: int, source: str, source_id: str) -> None:
    exists = db.execute(select(SourceRef).where(SourceRef.source == source, SourceRef.source_id == source_id)).scalar_one_or_none()
    if not exists:
        db.add(SourceRef(source=source, source_id=source_id, business_id=business_id))

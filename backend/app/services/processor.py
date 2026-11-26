"""Обробка знайденого бізнесу: нормалізація, дедуплікація, аналіз сайту, оцінка та збереження."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..analysis.evaluate import evaluate, split_links, valid_phone
from ..analysis.website import analyze_website
from ..models import Business
from ..sources.base import RawBusiness
from .dedup import add_source_ref, find_duplicate, normalize_address, normalize_name

MERGE_FIELDS = ("address", "city", "region", "country", "postcode", "lat", "lon", "phone", "email", "website",
                "instagram", "facebook", "map_url", "opening_hours", "brand", "rating", "reviews_count", "raw_type")


def business_to_eval_dict(biz: Business) -> dict:
    return {
        "name": biz.name, "category": biz.category, "address": biz.address, "phone": biz.phone, "email": biz.email,
        "website": biz.website, "instagram": biz.instagram, "facebook": biz.facebook, "socials": dict(biz.socials or {}),
        "opening_hours": biz.opening_hours, "rating": biz.rating, "reviews_count": biz.reviews_count, "menu_url": (biz.source_tags or {}).get("_menu_url"),
    }


def apply_evaluation(biz: Business, data: dict, wa: dict | None, scoring: dict, region_code: str | None) -> None:
    ev = evaluate(data, wa, scoring, region_code)
    # evaluate могла доповнити контакти/соцмережі з сайту
    for f in ("instagram", "facebook", "email", "phone"):
        if data.get(f) and not getattr(biz, f):
            setattr(biz, f, data[f])
    biz.socials = data.get("socials") or {}
    biz.website_status = ev["website_status"]
    biz.menu_status = ev["menu_status"]
    biz.booking_status = ev["booking_status"]
    biz.outdated_status = ev["outdated_status"]
    biz.problems = ev["problems"]
    biz.problem_details = ev["problem_details"]
    biz.lead_score = ev["lead_score"]
    biz.lead_tier = ev["lead_tier"]
    biz.score_breakdown = ev["score_breakdown"]
    biz.contact_verified = ev["contact_verified"]
    biz.phone_norm = ev["phone_norm"] or biz.phone_norm
    biz.recommended_services = ev["recommended_services"]
    biz.summary = ev["summary"]
    biz.recommendation = ev["recommendation"]
    biz.search_text = " ".join(x for x in [biz.name, biz.address, biz.city, biz.email, biz.phone, biz.phone_norm,
                                           biz.website, biz.instagram, biz.facebook] if x).lower()
    if wa is not None:
        biz.website_analysis = wa
        biz.last_checked_at = datetime.now(timezone.utc)


def upsert_raw(db: Session, raw: RawBusiness, *, check_website: bool, region_code: str | None = "UA"
               ) -> tuple[Business, bool, str | None, str | None]:
    """Крок 1: дедуплікація та створення/злиття запису. Повертає (бізнес, новий?, причина дубля, URL для перевірки)."""
    data = raw.to_dict()
    split_links(data)
    name_norm = normalize_name(data["name"])
    address_norm = normalize_address(data.get("address"))
    phone_norm = valid_phone(data.get("phone"), region_code)

    dup, reason = find_duplicate(db, source=raw.source, source_id=raw.source_id, name_norm=name_norm,
                                 phone_norm=phone_norm, address_norm=address_norm, lat=data.get("lat"), lon=data.get("lon"))
    if dup:
        biz = dup
        old_website = biz.website
        for f in MERGE_FIELDS:
            if data.get(f) not in (None, "") and getattr(biz, f) in (None, ""):
                setattr(biz, f, data[f])
        socials = dict(biz.socials or {})
        for k, v in (data.get("socials") or {}).items():
            socials.setdefault(k, v)
        biz.socials = socials
        srcs = list(biz.sources or [])
        if not any(s.get("source") == raw.source and s.get("source_id") == raw.source_id for s in srcs):
            srcs.append({"source": raw.source, "source_id": raw.source_id, "url": raw.source_url})
        biz.sources = srcs
        if biz.category == "other" and raw.category != "other":
            biz.category = raw.category
        if raw.menu_url and not (biz.source_tags or {}).get("_menu_url"):
            biz.source_tags = {**(biz.source_tags or {}), "_menu_url": raw.menu_url}
        need = check_website and biz.website and (biz.website != old_website or not (biz.website_analysis or {}).get("checked"))
        url = biz.website if need else None
    else:
        biz = Business(
            name=data["name"], name_norm=name_norm, category=raw.category, raw_type=data.get("raw_type"),
            address=data.get("address"), address_norm=address_norm, city=data.get("city"), region=data.get("region"),
            country=data.get("country"), postcode=data.get("postcode"), lat=data.get("lat"), lon=data.get("lon"),
            phone=data.get("phone"), phone_norm=phone_norm, email=data.get("email"), website=data.get("website"),
            instagram=data.get("instagram"), facebook=data.get("facebook"), socials=data.get("socials") or {},
            map_url=data.get("map_url"), opening_hours=data.get("opening_hours"), brand=data.get("brand"),
            rating=data.get("rating"), reviews_count=data.get("reviews_count"),
            sources=[{"source": raw.source, "source_id": raw.source_id, "url": raw.source_url}],
            source_tags={**(raw.tags or {}), **({"_menu_url": raw.menu_url} if raw.menu_url else {})},
        )
        db.add(biz)
        db.flush()
        url = biz.website if (check_website and biz.website) else None
    add_source_ref(db, biz.id, raw.source, raw.source_id)
    db.commit()
    return biz, dup is None, reason, url


def finalize(db: Session, biz: Business, wa: dict | None, scoring: dict, region_code: str | None = "UA") -> Business:
    """Крок 2: оцінка (wa=None — використати попередній аналіз, якщо він був)."""
    if wa is None and (biz.website_analysis or {}).get("checked") and biz.website:
        wa = biz.website_analysis
    apply_evaluation(biz, business_to_eval_dict(biz), wa, scoring, region_code)
    db.commit()
    return biz


def process_raw(db: Session, raw: RawBusiness, *, check_website: bool, scoring: dict, region_code: str | None = "UA"
                ) -> tuple[Business, bool, str | None]:
    biz, is_new, reason, url = upsert_raw(db, raw, check_website=check_website, region_code=region_code)
    wa = analyze_website(url) if url else None
    finalize(db, biz, wa, scoring, region_code)
    return biz, is_new, reason


def recheck_business(db: Session, biz: Business, scoring: dict, region_code: str | None = "UA") -> Business:
    """Повторна перевірка сайту, контактів і цифрової присутності."""
    data = business_to_eval_dict(biz)
    split_links(data)
    biz.website = data.get("website")
    biz.instagram = data.get("instagram") or biz.instagram
    biz.facebook = data.get("facebook") or biz.facebook
    wa = analyze_website(biz.website) if biz.website else {"checked": True, "status": "none", "checked_at": datetime.now(timezone.utc).isoformat()}
    apply_evaluation(biz, business_to_eval_dict(biz), wa, scoring, region_code)
    biz.last_checked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(biz)
    return biz


def rescore_all(db: Session, scoring: dict) -> int:
    """Перерахунок Lead Score для всієї бази (після зміни налаштувань оцінювання), без мережевих запитів."""
    n = 0
    for biz in db.query(Business).yield_per(200):
        wa = biz.website_analysis if biz.website_analysis and biz.website_analysis.get("checked") else None
        apply_evaluation(biz, business_to_eval_dict(biz), wa, scoring, None)
        n += 1
    db.commit()
    return n

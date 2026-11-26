from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..analysis.evaluate import valid_phone
from ..db import get_db
from ..models import Business, Note, SourceRef
from ..schemas import BusinessUpdate, NoteCreate, business_brief, business_full
from ..analysis.outreach import generate as generate_outreach
from ..services import settings_store
from ..services.dedup import normalize_address, normalize_name
from ..services.jobs import db_lock
from ..services.processor import business_to_eval_dict, apply_evaluation, recheck_business
from ..services.query import BusinessFilter, build_query
from .deps import business_filter

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


@router.get("")
def list_businesses(f: BusinessFilter = Depends(business_filter), page: int = Query(1, ge=1),
                    page_size: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    stmt = build_query(f)
    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "items": [business_brief(b) for b in rows]}


@router.get("/map")
def map_points(f: BusinessFilter = Depends(business_filter), db: Session = Depends(get_db)):
    rows = db.execute(build_query(f).where(Business.lat.is_not(None)).limit(5000)).scalars().all()
    return [{"id": b.id, "name": b.name, "lat": b.lat, "lon": b.lon, "lead_score": b.lead_score, "lead_tier": b.lead_tier,
             "category": b.category, "website_status": b.website_status, "address": b.address} for b in rows]


@router.get("/{bid}")
def get_business(bid: int, db: Session = Depends(get_db)):
    b = db.get(Business, bid)
    if not b:
        raise HTTPException(404, "Бізнес не знайдено")
    return business_full(b)


@router.patch("/{bid}")
def update_business(bid: int, upd: BusinessUpdate, db: Session = Depends(get_db)):
    with db_lock:
        b = db.get(Business, bid)
        if not b:
            raise HTTPException(404, "Бізнес не знайдено")
        data = upd.model_dump(exclude_unset=True)
        contact_changed = False
        for k, v in data.items():
            if k != "status":
                v = (v or "").strip() or None
                contact_changed = True
            setattr(b, k, v)
        if contact_changed:
            b.name_norm = normalize_name(b.name)
            b.address_norm = normalize_address(b.address)
            b.phone_norm = valid_phone(b.phone)
            if "website" in data:
                b.website_analysis = {}
            wa = b.website_analysis if (b.website_analysis or {}).get("checked") else None
            apply_evaluation(b, business_to_eval_dict(b), wa, settings_store.get_value(db, "scoring"), None)
        db.commit()
        db.refresh(b)
        return business_full(b)


@router.delete("/{bid}")
def delete_business(bid: int, db: Session = Depends(get_db)):
    with db_lock:
        b = db.get(Business, bid)
        if not b:
            raise HTTPException(404, "Бізнес не знайдено")
        db.execute(delete(SourceRef).where(SourceRef.business_id == bid))
        db.delete(b)
        db.commit()
    return {"ok": True}


@router.post("/{bid}/recheck")
def recheck(bid: int, db: Session = Depends(get_db)):
    b = db.get(Business, bid)
    if not b:
        raise HTTPException(404, "Бізнес не знайдено")
    with db_lock:
        b = recheck_business(db, b, settings_store.get_value(db, "scoring"))
    return business_full(b)


@router.get("/{bid}/outreach")
def outreach(bid: int, variant: int = Query(0, ge=0, le=10000), channel: str = Query("instagram", pattern="^(instagram|email)$"),
             db: Session = Depends(get_db)):
    """Готове повідомлення для першого контакту на основі виявлених проблем."""
    b = db.get(Business, bid)
    if not b:
        raise HTTPException(404, "Бізнес не знайдено")
    return generate_outreach(b, variant, channel, settings_store.get_value(db, "outreach"))


@router.post("/{bid}/notes")
def add_note(bid: int, body: NoteCreate, db: Session = Depends(get_db)):
    with db_lock:
        b = db.get(Business, bid)
        if not b:
            raise HTTPException(404, "Бізнес не знайдено")
        db.add(Note(business_id=bid, text=body.text.strip()))
        db.commit()
        db.refresh(b)
        return business_full(b)


@router.delete("/{bid}/notes/{nid}")
def delete_note(bid: int, nid: int, db: Session = Depends(get_db)):
    with db_lock:
        n = db.get(Note, nid)
        if not n or n.business_id != bid:
            raise HTTPException(404, "Нотатку не знайдено")
        db.delete(n)
        db.commit()
    return {"ok": True}

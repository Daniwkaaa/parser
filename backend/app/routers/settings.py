from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..analysis.evaluate import PROBLEM_LABELS, STATUS_LABELS
from ..categories import CATEGORIES, GROUP_LABELS
from ..db import get_db
from ..models import CLIENT_STATUSES
from ..schemas import ApiKeysUpdate, ScoringUpdate
from ..services import settings_store
from ..services.jobs import db_lock
from ..services.processor import rescore_all
from ..sources.registry import describe

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    return {
        "map": settings_store.get_value(db, "map"),
        "categories": [{"key": c.key, "label": c.label, "group": c.group, "offer_kind": c.offer_kind, "booking_kind": c.booking_kind} for c in CATEGORIES],
        "groups": GROUP_LABELS,
        "problems": PROBLEM_LABELS,
        "status_labels": STATUS_LABELS,
        "client_statuses": CLIENT_STATUSES,
        "sources": describe(),
    }


@router.get("/settings")
def get_settings_api(db: Session = Depends(get_db)):
    data = settings_store.all_settings(db)
    data["source_list"] = describe()
    return data


@router.put("/settings/scoring")
def put_scoring(body: ScoringUpdate, db: Session = Depends(get_db)):
    allowed = set(settings_store.DEFAULTS["scoring"]["weights"])
    weights = {k: max(0, min(100, int(v))) for k, v in body.weights.items() if k in allowed}
    th = {"high": int(body.thresholds.get("high", 70)), "medium": int(body.thresholds.get("medium", 40))}
    if not (0 <= th["medium"] < th["high"] <= 100):
        raise HTTPException(400, "Поріг «середній» має бути меншим за «високий» і в межах 0–100")
    with db_lock:
        settings_store.set_value(db, "scoring", {"weights": weights, "thresholds": th})
        n = rescore_all(db, settings_store.get_value(db, "scoring"))
    return {"scoring": settings_store.get_value(db, "scoring"), "rescored": n}


@router.put("/settings/sources")
def put_sources(body: dict[str, bool], db: Session = Depends(get_db)):
    with db_lock:
        return settings_store.set_value(db, "sources", {k: bool(v) for k, v in body.items()})


@router.put("/settings/search")
def put_search(body: dict, db: Session = Depends(get_db)):
    allowed = set(settings_store.DEFAULTS["search"])
    with db_lock:
        return settings_store.set_value(db, "search", {k: v for k, v in body.items() if k in allowed})


@router.put("/settings/outreach")
def put_outreach(body: dict, db: Session = Depends(get_db)):
    allowed = set(settings_store.DEFAULTS["outreach"])
    data = {k: str(v).strip()[:300] for k, v in body.items() if k in allowed}
    if data.get("gender") not in (None, "m", "f"):
        raise HTTPException(400, "gender: m або f")
    with db_lock:
        return settings_store.set_value(db, "outreach", data)


@router.put("/settings/map")
def put_map(body: dict, db: Session = Depends(get_db)):
    style = body.get("style", "dark")
    if style not in ("dark", "light", "custom"):
        raise HTTPException(400, "Невідомий стиль карти")
    url = (body.get("custom_url") or "").strip()
    if style == "custom" and not (url.startswith("https://") and "{z}" in url and "{x}" in url and "{y}" in url):
        raise HTTPException(400, "Вкажіть URL тайлів виду https://…/{z}/{x}/{y}.png")
    with db_lock:
        return settings_store.set_value(db, "map", {"style": style, "custom_url": url,
                                                    "custom_attribution": (body.get("custom_attribution") or "").strip()})


@router.put("/settings/api-keys")
def put_keys(body: ApiKeysUpdate, db: Session = Depends(get_db)):
    with db_lock:
        cur = settings_store.get_value(db, "api_keys") or {}
        for k, v in body.model_dump(exclude_unset=True).items():
            if v is not None:
                cur[k] = v.strip()
        settings_store.set_value(db, "api_keys", cur)
    return settings_store.all_settings(db)["api_keys"]


@router.post("/settings/reset-scoring")
def reset_scoring(db: Session = Depends(get_db)):
    with db_lock:
        settings_store.set_value(db, "scoring", settings_store.DEFAULTS["scoring"])
        n = rescore_all(db, settings_store.get_value(db, "scoring"))
    return {"scoring": settings_store.get_value(db, "scoring"), "rescored": n}

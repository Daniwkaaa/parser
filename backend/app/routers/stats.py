from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..analysis.evaluate import PROBLEM_LABELS
from ..categories import category_label
from ..db import get_db
from ..models import CLIENT_STATUSES, Business, SearchJob
from .search import job_dict

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    q = db.query(Business)
    total = q.count()
    no_site = q.filter(Business.website_status.in_(["no", "social_only"])).count()
    social_only = q.filter(Business.website_status == "social_only").count()
    no_menu = q.filter(Business.menu_status == "no").count()
    high = q.filter(Business.lead_tier == "high").count()
    medium = q.filter(Business.lead_tier == "medium").count()
    verified = q.filter(Business.contact_verified.is_(True)).count()
    avg = db.query(func.avg(Business.lead_score)).scalar() or 0

    by_cat = db.query(Business.category, func.count(), func.avg(Business.lead_score)).group_by(Business.category).all()
    by_status = dict(db.query(Business.status, func.count()).group_by(Business.status).all())
    by_tier = dict(db.query(Business.lead_tier, func.count()).group_by(Business.lead_tier).all())
    by_ws = dict(db.query(Business.website_status, func.count()).group_by(Business.website_status).all())
    problems = Counter()
    for (pl,) in db.query(Business.problems).all():
        problems.update(pl or [])
    buckets = [0] * 10
    for (s,) in db.query(Business.lead_score).all():
        buckets[min(9, (s or 0) // 10)] += 1
    jobs = db.query(SearchJob).order_by(SearchJob.id.desc()).limit(8).all()

    return {
        "totals": {"businesses": total, "no_website": no_site, "social_only": social_only, "no_menu": no_menu,
                   "high_potential": high, "medium_potential": medium, "verified_contacts": verified,
                   "avg_score": round(float(avg), 1)},
        "by_category": sorted([{"key": c, "label": category_label(c), "count": n, "avg_score": round(float(a or 0), 1)} for c, n, a in by_cat], key=lambda x: -x["count"]),
        "by_status": [{"key": k, "label": v, "count": by_status.get(k, 0)} for k, v in CLIENT_STATUSES.items()],
        "by_tier": [{"key": k, "label": lbl, "count": by_tier.get(k, 0)} for k, lbl in (("high", "Високий"), ("medium", "Середній"), ("low", "Низький"))],
        "by_website_status": by_ws,
        "by_problem": [{"key": k, "label": PROBLEM_LABELS[k], "count": problems.get(k, 0)} for k in PROBLEM_LABELS],
        "score_histogram": [{"range": f"{i*10}–{i*10+9 if i < 9 else 100}", "count": c} for i, c in enumerate(buckets)],
        "recent_jobs": [job_dict(j) for j in jobs],
    }

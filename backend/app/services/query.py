"""Фільтрація та сортування бази бізнесів (спільне для таблиці, карти й експорту)."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from ..models import Business, JobResult


@dataclass
class BusinessFilter:
    q: str | None = None
    categories: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    tiers: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    website_status: list[str] = field(default_factory=list)
    city: str | None = None
    min_score: int | None = None
    max_score: int | None = None
    has_contact: bool | None = None
    job_id: int | None = None
    sort: str = "lead_score"
    order: str = "desc"


SORTABLE = {"lead_score": Business.lead_score, "name": Business.name, "created_at": Business.created_at,
            "city": Business.city, "category": Business.category, "status": Business.status, "rating": Business.rating}


def build_query(f: BusinessFilter):
    stmt = select(Business)
    if f.q:
        like = f"%{f.q.strip().lower()}%"
        digits = "".join(ch for ch in f.q if ch.isdigit())
        conds = [Business.search_text.like(like), Business.name_norm.like(like)]
        if len(digits) >= 5:
            conds += [Business.phone_norm.like(f"%{digits.lstrip('0')}%")]
        stmt = stmt.where(or_(*conds))
    if f.categories:
        stmt = stmt.where(Business.category.in_(f.categories))
    if f.problems:
        # JSON-список зберігається як текст; шукаємо код у лапках (працює і в SQLite, і в PostgreSQL)
        stmt = stmt.where(or_(*[cast(Business.problems, String).like(f'%"{p}"%') for p in f.problems]))
    if f.tiers:
        stmt = stmt.where(Business.lead_tier.in_(f.tiers))
    if f.statuses:
        stmt = stmt.where(Business.status.in_(f.statuses))
    if f.website_status:
        stmt = stmt.where(Business.website_status.in_(f.website_status))
    if f.city:
        stmt = stmt.where(Business.search_text.like(f"%{f.city.strip().lower()}%"))
    if f.min_score is not None:
        stmt = stmt.where(Business.lead_score >= f.min_score)
    if f.max_score is not None:
        stmt = stmt.where(Business.lead_score <= f.max_score)
    if f.has_contact is not None:
        stmt = stmt.where(Business.contact_verified.is_(f.has_contact))
    if f.job_id:
        stmt = stmt.where(Business.id.in_(select(JobResult.business_id).where(JobResult.job_id == f.job_id)))
    col = SORTABLE.get(f.sort, Business.lead_score)
    # за однакового score вище ті, з ким можна зв'язатися, і з більшою кількістю даних
    stmt = stmt.order_by(col.desc() if f.order == "desc" else col.asc(), Business.contact_verified.desc(), Business.id.desc())
    return stmt


def run(db: Session, f: BusinessFilter):
    return db.execute(build_query(f)).scalars()

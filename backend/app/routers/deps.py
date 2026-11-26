from __future__ import annotations

from fastapi import Query

from ..services.query import BusinessFilter


def _split(v: str | None) -> list[str]:
    return [x for x in (v or "").split(",") if x]


def business_filter(
    q: str | None = None,
    categories: str | None = Query(None, description="через кому"),
    problems: str | None = None,
    tiers: str | None = None,
    statuses: str | None = None,
    website_status: str | None = None,
    city: str | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    has_contact: bool | None = None,
    job_id: int | None = None,
    sort: str = "lead_score",
    order: str = "desc",
) -> BusinessFilter:
    return BusinessFilter(q=q, categories=_split(categories), problems=_split(problems), tiers=_split(tiers),
                          statuses=_split(statuses), website_status=_split(website_status), city=city,
                          min_score=min_score, max_score=max_score, has_contact=has_contact, job_id=job_id,
                          sort=sort, order=order)

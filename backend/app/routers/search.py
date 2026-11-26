from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import JobLog, SearchJob
from ..schemas import GeocodeRequest, SearchRequest
from ..services.geocode import GeocodeError, resolve_area
from ..services.jobs import cancel_job, db_lock, start_job

router = APIRouter(prefix="/api", tags=["search"])


def job_dict(j: SearchJob) -> dict:
    p = {k: v for k, v in (j.params or {}).items() if not k.startswith("_")}
    return {
        "id": j.id, "status": j.status, "stage": j.stage, "params": p, "location_label": j.location_label,
        "progress_total": j.progress_total, "progress_done": j.progress_done, "found_count": j.found_count,
        "saved_count": j.saved_count, "new_count": j.new_count, "duplicate_count": j.duplicate_count,
        "skipped_count": j.skipped_count, "error": j.error,
        "area": (j.params or {}).get("_area"),
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
    }


@router.post("/geocode")
def geocode(req: GeocodeRequest, db: Session = Depends(get_db)):
    try:
        with db_lock:
            area = resolve_area(db, country=req.country, region=req.region, city=req.city, district=req.district, radius_km=req.radius_km)
    except GeocodeError as e:
        raise HTTPException(400, str(e))
    return area.to_dict()


@router.post("/search")
def create_search(req: SearchRequest, db: Session = Depends(get_db)):
    if not (req.city or req.region or (req.lat is not None and req.lon is not None)):
        raise HTTPException(400, "Вкажіть місто або регіон")
    with db_lock:
        job = SearchJob(params=req.model_dump(), status="queued", stage="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
    start_job(job.id)
    return job_dict(job)


@router.get("/jobs")
def list_jobs(limit: int = 30, db: Session = Depends(get_db)):
    jobs = db.query(SearchJob).order_by(SearchJob.id.desc()).limit(limit).all()
    return [job_dict(j) for j in jobs]


@router.get("/jobs/{jid}")
def get_job(jid: int, db: Session = Depends(get_db)):
    j = db.get(SearchJob, jid)
    if not j:
        raise HTTPException(404, "Завдання не знайдено")
    return job_dict(j)


@router.get("/jobs/{jid}/logs")
def job_logs(jid: int, after: int = 0, db: Session = Depends(get_db)):
    rows = db.query(JobLog).filter(JobLog.job_id == jid, JobLog.id > after).order_by(JobLog.id).limit(500).all()
    return [{"id": r.id, "ts": r.ts.isoformat(), "level": r.level, "message": r.message} for r in rows]


@router.post("/jobs/{jid}/cancel")
def cancel(jid: int, db: Session = Depends(get_db)):
    j = db.get(SearchJob, jid)
    if not j:
        raise HTTPException(404, "Завдання не знайдено")
    cancel_job(jid)
    return {"ok": True}


@router.post("/jobs/{jid}/resume")
def resume(jid: int, db: Session = Depends(get_db)):
    j = db.get(SearchJob, jid)
    if not j:
        raise HTTPException(404, "Завдання не знайдено")
    if j.status not in ("interrupted", "failed", "cancelled"):
        raise HTTPException(400, "Продовжити можна лише перерване, зупинене або невдале завдання")
    with db_lock:
        j.status = "queued"
        db.commit()
    start_job(jid)
    return job_dict(j)


@router.delete("/jobs/{jid}")
def delete_job(jid: int, db: Session = Depends(get_db)):
    """Видаляє лише запис про пошук; знайдені бізнеси залишаються в базі."""
    with db_lock:
        j = db.get(SearchJob, jid)
        if not j:
            raise HTTPException(404, "Завдання не знайдено")
        if j.status in ("running", "queued"):
            raise HTTPException(400, "Спочатку зупиніть завдання")
        db.query(JobLog).filter(JobLog.job_id == jid).delete()
        from ..models import JobResult
        db.query(JobResult).filter(JobResult.job_id == jid).delete()
        db.delete(j)
        db.commit()
    return {"ok": True}

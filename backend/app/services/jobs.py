"""Фонові завдання пошуку: збір, аналіз, збереження з проміжними результатами та відновленням."""
from __future__ import annotations

import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sqlalchemy import delete

from ..analysis.website import analyze_website
from ..config import get_settings
from ..db import SessionLocal
from ..models import Business, JobLog, JobResult, SearchJob, SourceRef
from ..sources.base import RawBusiness, SearchArea
from ..sources.registry import SOURCES
from . import settings_store
from ..regions import targets
from .geocode import GeocodeError, resolve_area
from .dedup import distance_m, normalize_name
from .processor import finalize, upsert_raw

log = logging.getLogger("leadfinder.jobs")
db_lock = threading.RLock()
_cancel: set[int] = set()
_running: dict[int, threading.Thread] = {}


def _now():
    return datetime.now(timezone.utc)


class JobContext:
    def __init__(self, job_id: int):
        self.job_id = job_id

    def log(self, level: str, message: str) -> None:
        getattr(log, "warning" if level == "warning" else ("error" if level == "error" else "info"))(f"[job {self.job_id}] {message}")
        with db_lock:
            db = SessionLocal()
            try:
                db.add(JobLog(job_id=self.job_id, level=level, message=message[:2000]))
                db.commit()
            finally:
                db.close()

    def update(self, **fields) -> None:
        with db_lock:
            db = SessionLocal()
            try:
                job = db.get(SearchJob, self.job_id)
                for k, v in fields.items():
                    setattr(job, k, v)
                db.commit()
            finally:
                db.close()

    @property
    def cancelled(self) -> bool:
        return self.job_id in _cancel


def start_job(job_id: int) -> None:
    if job_id in _running and _running[job_id].is_alive():
        return
    _cancel.discard(job_id)
    t = threading.Thread(target=_run, args=(job_id,), daemon=True, name=f"job-{job_id}")
    _running[job_id] = t
    t.start()


def cancel_job(job_id: int) -> None:
    _cancel.add(job_id)


def recover_interrupted() -> None:
    """При запуску: завдання, що виконувалися під час зупинки програми, позначаємо як перервані."""
    db = SessionLocal()
    try:
        for job in db.query(SearchJob).filter(SearchJob.status.in_(["running", "queued"])).all():
            job.status = "interrupted"
            job.error = "Програму було зупинено під час виконання. Можна продовжити з місця зупинки."
            db.add(JobLog(job_id=job.id, level="warning", message="Завдання перервано зупинкою програми"))
        db.commit()
    finally:
        db.close()


def detect_chains(cands: list[RawBusiness], min_locations: int = 2, min_distance_m: float = 300) -> set[str]:
    """Мережа = та сама назва в кількох різних місцях (далі ніж min_distance_m) або тег brand у будь-якої з точок.

    OSM часто не має тегу brand для локальних мереж, тому дивимося на повтори назви в межах пошуку.
    """
    groups: dict[str, list[RawBusiness]] = {}
    for c in cands:
        key = normalize_name(c.name)
        if len(key) >= 3:
            groups.setdefault(key, []).append(c)
    chains: set[str] = set()
    for key, items in groups.items():
        if any(i.brand for i in items):
            chains.add(key)
            continue
        spots: list[RawBusiness] = []
        for i in items:
            if all(distance_m(i.lat, i.lon, j.lat, j.lon) > min_distance_m for j in spots):
                spots.append(i)
        if len(spots) >= min_locations:
            chains.add(key)
    return chains


def _matches(problems: list[str], wanted: list[str]) -> bool:
    if not wanted:
        return True
    return any(p in problems for p in wanted)


def _run(job_id: int) -> None:
    ctx = JobContext(job_id)
    db = SessionLocal()
    try:
        job = db.get(SearchJob, job_id)
        params = dict(job.params or {})
        resuming = bool(job.candidates) or bool(params.get("_targets_done"))
        ctx.update(status="running", stage="geocode", started_at=job.started_at or _now(), error=None, finished_at=None)
        ctx.log("info", "Продовжую перерване завдання" if resuming else "Завдання запущено")

        scoring = settings_store.get_value(db, "scoring")
        limit = int(params.get("limit") or 100)
        wanted = [] if params.get("comprehensive") else list(params.get("problems") or [])
        check_websites = bool(params.get("check_websites", True))
        exclude_chains = bool(params.get("exclude_chains", True))

        scope = params.get("scope") or "city"
        sources = params.get("sources") or ["osm"]
        categories = params.get("categories") or []

        def fetch(area: SearchArea, per_limit: int, target_idx: int) -> list[RawBusiness]:
            got: list[RawBusiness] = []
            for src_key in sources:
                cls = SOURCES.get(src_key)
                if not cls:
                    continue
                api_key = settings_store.get_api_key(db, src_key) if cls.requires_key else None
                src = cls(api_key=api_key)
                if not src.is_available():
                    ctx.log("warning", f"{cls.label}: не задано API-ключ, джерело пропущено")
                    continue
                try:
                    found = src.search(area, categories, per_limit, ctx.log)
                except Exception as e:  # помилка одного джерела чи міста не зупиняє решту
                    ctx.log("error", f"{cls.label}: помилка — {e}")
                    continue
                for f in found:
                    f.tags = {**(f.tags or {}), "_target": target_idx}
                got.extend(found)
            return got

        def save_partial(cands: list[RawBusiness], **extra) -> None:
            ctx.update(candidates=[c.to_dict() for c in cands], found_count=len(cands), params=params, **extra)

        # 1–2. Територія і збір кандидатів (проміжні результати зберігаються після кожного міста)
        collected = bool(params.get("_collected")) or (bool(job.candidates) and scope == "city")
        candidates = [RawBusiness.from_dict(c) for c in (job.candidates or [])]
        region_code = "UA"
        if collected:
            ctx.log("info", f"Використовую збережені проміжні результати: {len(candidates)} кандидатів")
            if params.get("_area"):
                region_code = SearchArea.from_dict(params["_area"]).country_code or "UA"
        elif scope == "city":
            if params.get("_area"):
                area = SearchArea.from_dict(params["_area"])
            else:
                ctx.log("info", "Визначаю територію пошуку через Nominatim…")
                with db_lock:
                    area = resolve_area(db, country=params.get("country"), region=params.get("region"), city=params.get("city"),
                                        district=params.get("district"), radius_km=params.get("radius_km"),
                                        lat=params.get("lat"), lon=params.get("lon"))
                params["_area"] = area.to_dict()
                ctx.update(params=params, location_label=area.label)
                ctx.log("info", f"Територія: {area.label}")
            region_code = area.country_code or "UA"
            ctx.update(stage="collect")
            candidates = fetch(area, limit, 0)
        else:
            tgts = targets(scope, params.get("region"))
            label = f"{params.get('region')} — {len(tgts)} міст" if scope == "oblast" else f"Україна (підконтрольна територія) — до {len(tgts)} міст"
            ctx.update(stage="collect", location_label=label)
            enough = limit * 3
            per_city = max(30, -(-limit * 2 // min(len(tgts), 24)))
            done = int(params.get("_targets_done") or 0)
            ctx.log("info", f"Пошук по {label}. Міста обробляються по черзі з паузами, щоб не перевантажувати сервери OSM.")
            for i in range(done, len(tgts)):
                if ctx.cancelled or len(candidates) >= enough:
                    break
                city, region = tgts[i]
                try:
                    with db_lock:
                        area = resolve_area(db, country="Україна", region=None if region == "Київ" else region, city=city)
                except GeocodeError as e:
                    ctx.log("warning", f"{city}: не вдалося визначити територію ({e}), пропускаю")
                    params["_targets_done"] = i + 1
                    continue
                got = fetch(area, per_city, i)
                candidates.extend(got)
                params["_targets_done"] = i + 1
                save_partial(candidates, progress_total=len(tgts), progress_done=i + 1)
                ctx.log("info", f"{city} ({region}): {len(got)} кандидатів, усього {len(candidates)}")
            if ctx.cancelled:
                ctx.update(status="cancelled", stage="cancelled", finished_at=_now())
                ctx.log("warning", "Завдання зупинено користувачем; зібрані дані збережено, можна продовжити")
                return
            # чергуємо міста, щоб ліміт заповнювався з усіх, а не лише з першого
            buckets: dict[int, list[RawBusiness]] = {}
            for c in candidates:
                buckets.setdefault(int((c.tags or {}).get("_target", 0)), []).append(c)
            order = sorted(buckets)
            mixed: list[RawBusiness] = []
            j = 0
            while any(j < len(buckets[k]) for k in order):
                for k in order:
                    if j < len(buckets[k]):
                        mixed.append(buckets[k][j])
                j += 1
            candidates = mixed

        if not collected:
            if exclude_chains:
                chains = detect_chains(candidates)
                before = len(candidates)
                excluded = sorted({c.name for c in candidates if c.brand or normalize_name(c.name) in chains})
                candidates = [c for c in candidates if not c.brand and normalize_name(c.name) not in chains]
                if before - len(candidates):
                    sample = ", ".join(excluded[:8]) + ("…" if len(excluded) > 8 else "")
                    ctx.log("info", f"Виключено мережевих закладів: {before - len(candidates)} ({sample})")
            params["_collected"] = True
            save_partial(candidates, progress_total=len(candidates), progress_done=0)
            ctx.log("info", f"Знайдено кандидатів: {len(candidates)}")
            if not candidates:
                ctx.update(status="completed", stage="done", finished_at=_now())
                ctx.log("warning", "Нічого не знайдено. Спробуйте збільшити радіус або обрати інші категорії.")
                return

        processed = set(params.get("_processed") or [])
        keys = ("saved_count", "new_count", "duplicate_count", "skipped_count", "progress_done")
        # якщо збір щойно завершився — аналіз починається з нуля; інакше продовжуємо лічильники
        counters: dict[str, int] = {k: (getattr(job, k) or 0) if collected else 0 for k in keys}
        ctx.update(stage="analyze", progress_total=len(candidates))
        ctx.log("info", "Аналізую цифрову присутність (перевірка сайтів)…" if check_websites else "Аналізую дані (без перевірки сайтів)…")

        pending = [c for c in candidates if f"{c.source}:{c.source_id}" not in processed]

        def handle(raw: RawBusiness):
            if ctx.cancelled:
                return None
            with db_lock:
                if counters["saved_count"] >= limit:
                    return None
                s = SessionLocal()
                try:
                    biz, is_new, reason, url = upsert_raw(s, raw, check_website=check_websites, region_code=region_code)
                    biz_id = biz.id
                finally:
                    s.close()
            wa = analyze_website(url) if url else None  # мережевий запит — поза блокуванням
            with db_lock:
                s = SessionLocal()
                try:
                    biz = s.get(Business, biz_id)
                    finalize(s, biz, wa, scoring, region_code)
                    matched = _matches(biz.problems or [], wanted)
                    key = f"{raw.source}:{raw.source_id}"
                    processed.add(key)
                    counters["progress_done"] += 1
                    if not is_new:
                        counters["duplicate_count"] += 1
                    if matched and counters["saved_count"] < limit:
                        counters["saved_count"] += 1
                        if is_new:
                            counters["new_count"] += 1
                        if not s.query(JobResult).filter_by(job_id=job_id, business_id=biz_id).first():
                            s.add(JobResult(job_id=job_id, business_id=biz_id, is_new=is_new))
                        s.commit()
                        status = "новий" if is_new else f"дубль ({reason}) — дані об'єднано"
                        ctx.log("info", f"✓ {biz.name}: {biz.lead_score} балів, {status}")
                    else:
                        # не відповідає фільтрам або ліміт уже досягнуто паралельними потоками:
                        # новий запис не залишаємо в базі, щоб база збігалася зі звітом завдання
                        if matched:
                            counters["overflow"] = counters.get("overflow", 0) + 1
                        else:
                            counters["skipped_count"] += 1
                        if is_new:
                            s.execute(delete(JobResult).where(JobResult.business_id == biz_id))
                            s.execute(delete(SourceRef).where(SourceRef.business_id == biz_id))
                            s.delete(biz)
                            s.commit()
                    p = dict(params)
                    p["_processed"] = list(processed)
                    ctx.update(params=p, **{k: v for k, v in counters.items() if k != "overflow"})
                finally:
                    s.close()
            return True

        workers = max(1, int(get_settings().website_check_concurrency)) if check_websites else 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(handle, c) for c in pending]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    ctx.log("error", f"Помилка обробки запису: {e}")
                    log.debug(traceback.format_exc())

        if ctx.cancelled:
            ctx.update(status="cancelled", stage="cancelled", finished_at=_now())
            ctx.log("warning", "Завдання зупинено користувачем")
        else:
            ctx.update(status="completed", stage="done", finished_at=_now())
            ctx.log("info", f"Готово: збережено {counters['saved_count']} (нових {counters['new_count']}, дублікатів {counters['duplicate_count']}, не відповідали фільтрам {counters['skipped_count']})")
    except GeocodeError as e:
        ctx.update(status="failed", stage="failed", error=str(e), finished_at=_now())
        ctx.log("error", str(e))
    except Exception as e:
        log.exception("job %s failed", job_id)
        ctx.update(status="failed", stage="failed", error=str(e), finished_at=_now())
        ctx.log("error", f"Помилка: {e}. Збережені результати не втрачено, завдання можна продовжити.")
    finally:
        db.close()
        _cancel.discard(job_id)

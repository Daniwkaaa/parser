"""ORM-моделі."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


CLIENT_STATUSES = {
    "new": "Новий",
    "checked": "Перевірений",
    "potential": "Потенційний клієнт",
    "contacted": "Контакт встановлено",
    "replied": "Відповів",
    "not_interested": "Не зацікавлений",
    "in_progress": "У роботі",
    "deal": "Укладено угоду",
}


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    name_norm: Mapped[str] = mapped_column(String(300), index=True, default="")
    category: Mapped[str] = mapped_column(String(50), index=True, default="other")
    raw_type: Mapped[str | None] = mapped_column(String(120))

    address: Mapped[str | None] = mapped_column(String(500))
    address_norm: Mapped[str | None] = mapped_column(String(500), index=True)
    search_text: Mapped[str] = mapped_column(Text, default="")  # нижній регістр для пошуку (SQLite не знижує кирилицю)
    city: Mapped[str | None] = mapped_column(String(150), index=True)
    region: Mapped[str | None] = mapped_column(String(150))
    country: Mapped[str | None] = mapped_column(String(100))
    postcode: Mapped[str | None] = mapped_column(String(20))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)

    phone: Mapped[str | None] = mapped_column(String(200))
    phone_norm: Mapped[str | None] = mapped_column(String(40), index=True)
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    instagram: Mapped[str | None] = mapped_column(String(300))
    facebook: Mapped[str | None] = mapped_column(String(300))
    socials: Mapped[dict] = mapped_column(JSON, default=dict)  # telegram, viber, tiktok, youtube, whatsapp
    map_url: Mapped[str | None] = mapped_column(String(500))
    opening_hours: Mapped[str | None] = mapped_column(String(300))
    brand: Mapped[str | None] = mapped_column(String(200))
    rating: Mapped[float | None] = mapped_column(Float)
    reviews_count: Mapped[int | None] = mapped_column(Integer)
    sources: Mapped[list] = mapped_column(JSON, default=list)  # [{source, source_id, url}]
    source_tags: Mapped[dict] = mapped_column(JSON, default=dict)

    # результати аналізу
    website_status: Mapped[str] = mapped_column(String(20), default="unknown")  # yes|no|social_only|unreachable|unknown
    menu_status: Mapped[str] = mapped_column(String(20), default="unknown")  # yes|no|unknown|na
    booking_status: Mapped[str] = mapped_column(String(20), default="unknown")  # yes|no|unknown|na
    outdated_status: Mapped[str] = mapped_column(String(20), default="unknown")  # yes|no|unknown|na
    website_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    problems: Mapped[list] = mapped_column(JSON, default=list)  # коди проблем
    problem_details: Mapped[list] = mapped_column(JSON, default=list)  # [{code, text}]
    summary: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    recommended_services: Mapped[list] = mapped_column(JSON, default=list)
    lead_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score_breakdown: Mapped[list] = mapped_column(JSON, default=list)
    lead_tier: Mapped[str] = mapped_column(String(10), default="low", index=True)
    contact_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(30), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notes: Mapped[list["Note"]] = relationship(back_populates="business", cascade="all, delete-orphan", order_by="Note.created_at.desc()")


class SourceRef(Base):
    """Ідентифікатор бізнесу в зовнішньому джерелі (для точної дедуплікації)."""
    __tablename__ = "source_refs"
    __table_args__ = (UniqueConstraint("source", "source_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(200))
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    business: Mapped[Business] = relationship(back_populates="notes")


class SearchJob(Base):
    __tablename__ = "search_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|running|completed|failed|interrupted|cancelled
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    location_label: Mapped[str | None] = mapped_column(String(300))
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, default=0)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    candidates: Mapped[list] = mapped_column(JSON, default=list)  # проміжні результати збору
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobLog(Base):
    __tablename__ = "job_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("search_jobs.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    level: Mapped[str] = mapped_column(String(10), default="info")
    message: Mapped[str] = mapped_column(Text)


class JobResult(Base):
    __tablename__ = "job_results"
    __table_args__ = (UniqueConstraint("job_id", "business_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("search_jobs.id", ondelete="CASCADE"), index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"
    query: Mapped[str] = mapped_column(String(500), primary_key=True)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

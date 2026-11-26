"""Конфігурація застосунку через змінні середовища / файл .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'leadfinder.db').as_posix()}"
    app_user_agent: str = "LeadFinder/1.0 (+https://github.com/Daniwkaaa/parser)"
    contact_email: str = ""

    overpass_urls: str = "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter"
    nominatim_url: str = "https://nominatim.openstreetmap.org"

    google_places_api_key: str = ""
    serpapi_api_key: str = ""

    http_timeout: float = 15.0
    website_check_concurrency: int = 4
    respect_robots_txt: bool = True

    log_level: str = "INFO"
    frontend_dist: str = str(BASE_DIR.parent / "frontend" / "dist")

    @property
    def overpass_url_list(self) -> list[str]:
        return [u.strip() for u in self.overpass_urls.split(",") if u.strip()]

    @property
    def user_agent(self) -> str:
        ua = self.app_user_agent
        if self.contact_email and self.contact_email not in ua:
            ua = f"{ua} {self.contact_email}"
        return ua


@lru_cache
def get_settings() -> Settings:
    return Settings()

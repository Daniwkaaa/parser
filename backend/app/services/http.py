"""HTTP-клієнт з обмеженням частоти запитів, тайм-аутами та повторними спробами."""
from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter

from ..config import get_settings

log = logging.getLogger("leadfinder.http")


class HostRateLimiter:
    """Мінімальний інтервал між запитами до одного хоста (потокобезпечно)."""

    def __init__(self, default_interval: float = 1.0):
        self.default_interval = default_interval
        self.intervals: dict[str, float] = {}
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def set_interval(self, host: str, seconds: float) -> None:
        self.intervals[host] = seconds

    def wait(self, url: str) -> None:
        host = urlparse(url).hostname or ""
        interval = self.intervals.get(host, self.default_interval)
        with self._lock:
            now = time.monotonic()
            ready = self._next.get(host, 0.0)
            delay = max(0.0, ready - now)
            self._next[host] = max(now, ready) + interval
        if delay:
            time.sleep(delay)


rate_limiter = HostRateLimiter(default_interval=1.0)
# Правила Nominatim: не більше 1 запиту/с. Overpass: помірно, з паузами.
rate_limiter.set_interval("nominatim.openstreetmap.org", 1.1)
rate_limiter.set_interval("overpass-api.de", 2.0)
rate_limiter.set_interval("overpass.kumi.systems", 2.0)

_local = threading.local()


def session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": get_settings().user_agent, "Accept-Language": "uk,en;q=0.8"})
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=0)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        _local.session = s
    return s


class HttpError(Exception):
    pass


def request(method: str, url: str, *, retries: int = 2, backoff: float = 3.0, timeout: float | None = None,
            retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504), rate_limit: bool = True, **kw) -> requests.Response:
    timeout = timeout or get_settings().http_timeout
    last: Exception | None = None
    for attempt in range(retries + 1):
        if rate_limit:
            rate_limiter.wait(url)
        try:
            resp = session().request(method, url, timeout=timeout, **kw)
            if resp.status_code in retry_statuses and attempt < retries:
                wait = backoff * (attempt + 1)
                ra = resp.headers.get("Retry-After")
                if ra and ra.isdigit():
                    wait = max(wait, min(int(ra), 60))
                log.warning("HTTP %s від %s, повтор через %.0f с", resp.status_code, urlparse(url).hostname, wait)
                time.sleep(wait)
                continue
            return resp
        except requests.RequestException as e:  # мережеві помилки / тайм-аути
            last = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
    raise HttpError(f"Запит до {urlparse(url).hostname} не вдався: {last}")

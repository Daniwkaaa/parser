"""LeadFinder — пошук бізнесів зі слабкою цифровою присутністю."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, get_settings
from .db import init_db
from .routers import businesses, export, search, settings, stats
from .services.jobs import recover_interrupted

settings_ = get_settings()
(BASE_DIR / "data").mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings_.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(BASE_DIR / "data" / "leadfinder.log", encoding="utf-8")],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recover_interrupted()
    yield


app = FastAPI(title="LeadFinder API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])

for r in (businesses.router, search.router, stats.router, settings.router, export.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logging.getLogger("leadfinder").exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Внутрішня помилка: {exc}"})


# Зібраний фронтенд (npm run build) віддається тим самим сервером
dist = Path(settings_.frontend_dist)
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = dist / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(dist / "index.html")

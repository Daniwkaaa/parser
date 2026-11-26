from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.export import to_csv, to_xlsx
from ..services.query import BusinessFilter, run
from .deps import business_filter

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export")
def export(format: str = Query("xlsx", pattern="^(csv|xlsx)$"), ids: str | None = None,
           f: BusinessFilter = Depends(business_filter), db: Session = Depends(get_db)):
    rows = list(run(db, f))
    if ids:
        wanted = {int(x) for x in ids.split(",") if x.isdigit()}
        rows = [r for r in rows if r.id in wanted]
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    if format == "csv":
        return Response(to_csv(rows), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="leads-{stamp}.csv"'})
    return Response(to_xlsx(rows), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="leads-{stamp}.xlsx"'})

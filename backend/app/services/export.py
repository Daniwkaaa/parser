"""Експорт у CSV та XLSX."""
from __future__ import annotations

import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..analysis.evaluate import PROBLEM_LABELS, STATUS_LABELS
from ..categories import category_label
from ..models import CLIENT_STATUSES, Business

COLUMNS = [
    ("Назва", lambda b: b.name),
    ("Категорія", lambda b: category_label(b.category)),
    ("Lead Score", lambda b: b.lead_score),
    ("Потенціал", lambda b: {"high": "Високий", "medium": "Середній", "low": "Низький"}.get(b.lead_tier, b.lead_tier)),
    ("Статус клієнта", lambda b: CLIENT_STATUSES.get(b.status, b.status)),
    ("Адреса", lambda b: b.address),
    ("Місто", lambda b: b.city),
    ("Телефон", lambda b: b.phone),
    ("Email", lambda b: b.email),
    ("Вебсайт", lambda b: b.website),
    ("Instagram", lambda b: b.instagram),
    ("Facebook", lambda b: b.facebook),
    ("Інші соцмережі", lambda b: ", ".join(f"{k}: {v}" for k, v in (b.socials or {}).items())),
    ("Сайт", lambda b: STATUS_LABELS.get(b.website_status, b.website_status)),
    ("Онлайн-меню/каталог", lambda b: STATUS_LABELS.get(b.menu_status, b.menu_status)),
    ("Онлайн-запис/бронювання", lambda b: STATUS_LABELS.get(b.booking_status, b.booking_status)),
    ("Застарілий сайт", lambda b: STATUS_LABELS.get(b.outdated_status, b.outdated_status)),
    ("Проблеми", lambda b: "; ".join(PROBLEM_LABELS.get(p, p) for p in (b.problems or []))),
    ("Опис", lambda b: b.summary),
    ("Рекомендація", lambda b: b.recommendation),
    ("Послуги для пропозиції", lambda b: "; ".join(b.recommended_services or [])),
    ("Рейтинг", lambda b: b.rating),
    ("Відгуків", lambda b: b.reviews_count),
    ("Графік роботи", lambda b: b.opening_hours),
    ("Широта", lambda b: b.lat),
    ("Довгота", lambda b: b.lon),
    ("Посилання на карту", lambda b: b.map_url),
    ("Джерела", lambda b: ", ".join(s.get("source", "") for s in (b.sources or []))),
    ("Нотатки", lambda b: " | ".join(n.text for n in b.notes)),
    ("Додано", lambda b: b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else None),
]


def to_csv(rows: list[Business]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([c for c, _ in COLUMNS])
    for b in rows:
        w.writerow(["" if (v := fn(b)) is None else v for _, fn in COLUMNS])
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM — щоб Excel коректно показав кирилицю


def to_xlsx(rows: list[Business]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Бізнеси"
    ws.append([c for c, _ in COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="312E81")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    fills = {"high": "DCFCE7", "medium": "FEF9C3", "low": "F3F4F6"}
    for b in rows:
        ws.append([fn(b) for _, fn in COLUMNS])
        ws.cell(row=ws.max_row, column=3).fill = PatternFill("solid", fgColor=fills.get(b.lead_tier, "FFFFFF"))
    widths = [32, 22, 10, 11, 18, 36, 14, 18, 26, 30, 30, 30, 30, 14, 16, 18, 14, 40, 60, 60, 50, 8, 9, 30, 10, 10, 40, 14, 40, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

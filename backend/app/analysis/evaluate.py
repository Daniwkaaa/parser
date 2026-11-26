"""Оцінка цифрової присутності: статуси, проблеми, Lead Score, рекомендації.

Кожен висновок спирається на дані з джерела або на результат перевірки сайту.
Якщо даних немає — статус «unknown» (не перевірено), і проблема не нараховується.
"""
from __future__ import annotations

import re
from typing import Any

import phonenumbers

from ..categories import HIGH_VALUE, get_category
from .website import classify_url, normalize_url, social_network_of

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

PROBLEM_LABELS = {
    "no_website": "Без вебсайту",
    "social_only": "Лише Instagram / Facebook",
    "website_unreachable": "Сайт не працює",
    "no_menu": "Без онлайн-меню / каталогу",
    "no_booking": "Без онлайн-запису",
    "no_reservation": "Без системи бронювання",
    "outdated_website": "Застарілий вебсайт",
    "website_improvable": "Сайт є, але є потенціал для покращення",
    "incomplete_info": "Неповна інформація про бізнес",
}

STATUS_LABELS = {
    "yes": "Є", "no": "Відсутній", "social_only": "Лише соцмережі", "unreachable": "Не працює",
    "unknown": "Не перевірено", "na": "Не застосовується",
}


def valid_phone(phone: str | None, region: str | None = "UA") -> str | None:
    """Повертає E.164 для першого валідного номера або None."""
    if not phone:
        return None
    for part in re.split(r"[;,/]|\s{2,}", phone):
        part = part.strip()
        if not part:
            continue
        try:
            num = phonenumbers.parse(part, region or "UA")
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    return None


def valid_email(email: str | None) -> bool:
    return bool(email and EMAIL_RE.match(email.strip()))


def split_links(b: dict) -> None:
    """Якщо в полі website вказано соцмережу — переносимо її у відповідне поле."""
    w = b.get("website")
    if not w:
        return
    kind = classify_url(w)
    if kind == "social":
        net = social_network_of(w)
        if net == "instagram" and not b.get("instagram"):
            b["instagram"] = w
        elif net == "facebook" and not b.get("facebook"):
            b["facebook"] = w
        elif net:
            b.setdefault("socials", {}).setdefault(net, w)
        b["website"] = None
        b.setdefault("_social_from_website", True)
    elif kind == "linkpage":
        b.setdefault("socials", {}).setdefault("linkpage", w)
        b["website"] = None


def social_url(net: str, value: str) -> str:
    v = value.strip()
    if v.startswith("http"):
        return v
    v = v.lstrip("@")
    base = {"instagram": "https://instagram.com/", "facebook": "https://facebook.com/", "telegram": "https://t.me/", "tiktok": "https://tiktok.com/@"}
    return base.get(net, "") + v if net in base else v


def evaluate(b: dict, wa: dict | None, scoring: dict, region_code: str | None = "UA") -> dict[str, Any]:
    """b — поля бізнесу; wa — результат analyze_website або None (не перевірявся)."""
    cat = get_category(b.get("category"))
    offer_kind = cat.offer_kind if cat else "services"
    booking_kind = cat.booking_kind if cat else "none"
    weights = scoring.get("weights", {})
    thr = scoring.get("thresholds", {"high": 70, "medium": 40})

    socials = dict(b.get("socials") or {})
    if wa and wa.get("socials"):
        for net, url in wa["socials"].items():
            if net == "instagram" and not b.get("instagram"):
                b["instagram"] = url
            elif net == "facebook" and not b.get("facebook"):
                b["facebook"] = url
            elif net not in ("instagram", "facebook"):
                socials.setdefault(net, url)
    b["socials"] = socials
    has_social = bool(b.get("instagram") or b.get("facebook") or socials.get("tiktok") or socials.get("linkpage"))

    # контакти з сайту доповнюють відсутні
    if wa:
        if not b.get("email") and wa.get("emails"):
            b["email"] = wa["emails"][0]
        if not b.get("phone") and wa.get("phones"):
            b["phone"] = wa["phones"][0]

    # --- статус сайту ---
    website = b.get("website")
    if website:
        st = (wa or {}).get("status", "unknown")
        if st in ("social", "linkpage"):
            website_status = "social_only"
        elif st in ("ok", "parked"):
            website_status = "yes"
        elif st == "unreachable":
            website_status = "unreachable"
        else:
            website_status = "unknown"
    else:
        website_status = "social_only" if has_social else "no"

    site_ok = website_status == "yes" and (wa or {}).get("status") == "ok"
    parked = (wa or {}).get("status") == "parked"
    no_own_site = website_status in ("no", "social_only") or parked

    # --- меню / каталог / послуги ---
    if offer_kind in ("menu", "catalog"):
        flag = "has_menu" if offer_kind == "menu" else "has_catalog"
        if b.get("menu_url"):
            menu_status = "yes"
        elif site_ok:
            menu_status = "yes" if (wa.get(flag) or (offer_kind == "catalog" and wa.get("has_menu"))) else "no"
        elif no_own_site or website_status == "unreachable":
            menu_status = "no"
        else:
            menu_status = "unknown"
    else:
        menu_status = "na"

    # --- запис / бронювання ---
    if booking_kind == "none":
        booking_status = "na"
    elif site_ok:
        booking_status = "yes" if wa.get("has_booking") else "no"
    elif no_own_site or website_status == "unreachable":
        booking_status = "no"
    else:
        booking_status = "unknown"

    # --- застарілість ---
    if site_ok or parked:
        outdated_status = "yes" if (wa.get("is_outdated") or parked) else "no"
    elif website_status == "unknown":
        outdated_status = "unknown"
    else:
        outdated_status = "na"

    phone_e164 = valid_phone(b.get("phone"), region_code)
    email_ok = valid_email(b.get("email"))
    contact_verified = bool(phone_e164 or email_ok)

    problems: list[str] = []
    details: list[dict] = []
    name = b.get("name", "")

    def add(code: str, text: str):
        problems.append(code)
        details.append({"code": code, "label": PROBLEM_LABELS[code], "text": text})

    if website_status == "no":
        add("no_website", "Власного сайту не знайдено: у джерелі не вказано ні сайту, ні сторінок у соцмережах.")
    elif website_status == "social_only":
        nets = [n for n in ("instagram", "facebook") if b.get(n)] + [n for n in socials if n in ("tiktok", "linkpage", "telegram")]
        add("no_website", "Власного сайту немає — замість нього вказано лише сторінку в соцмережі.")
        add("social_only", f"Онлайн-присутність обмежується соцмережами: {', '.join(nets)}.")
    elif website_status == "unreachable":
        add("website_unreachable", f"Сайт {website} вказано, але він не відкривається ({(wa or {}).get('error') or 'помилка'}).")
    if parked:
        add("outdated_website", "Сайт є лише заглушкою («у розробці» або припаркований домен).")

    if menu_status == "no":
        what = "онлайн-меню" if offer_kind == "menu" else "онлайн-каталогу товарів"
        why = "на сайті не знайдено розділу чи посилання" if site_ok else "немає працюючого власного сайту, а посилання на меню в джерелі не вказане"
        add("no_menu", f"Немає {what}: {why}.")
    if booking_status == "no":
        code = "no_reservation" if booking_kind == "reservation" else "no_booking"
        what = "системи онлайн-бронювання" if booking_kind == "reservation" else "онлайн-запису"
        why = "на сайті не знайдено віджета чи кнопки" if site_ok else "немає працюючого власного сайту"
        add(code, f"Немає {what}: {why}. Клієнти можуть домовитися лише телефоном або в повідомленнях.")
    if site_ok and outdated_status == "yes":
        sig = "; ".join(s["text"] for s in wa.get("outdated_signals", [])[:4])
        add("outdated_website", f"Сайт має ознаки застарілості: {sig}.")
    elif site_ok:
        imp = [s["text"] for s in wa.get("outdated_signals", [])] + list(wa.get("improvement_signals", []))
        if offer_kind == "services" and not wa.get("has_services"):
            imp.append("Немає окремого розділу з послугами та цінами")
        if imp:
            add("website_improvable", "Є що покращити: " + "; ".join(imp[:5]) + ".")

    missing = []
    if not b.get("address"):
        missing.append("адреса")
    if not b.get("opening_hours"):
        missing.append("графік роботи")
    if not (b.get("phone") or b.get("email")):
        missing.append("телефон чи email")
    if len(missing) >= 2 or "телефон чи email" in missing:
        add("incomplete_info", "У відкритих джерелах бракує: " + ", ".join(missing) + ".")

    # --- Lead Score ---
    breakdown = []

    def score(key: str, label: str):
        w = int(weights.get(key, 0) or 0)
        if w:
            breakdown.append({"key": key, "label": label, "points": w})

    if "no_website" in problems:
        score("no_website", "Немає власного сайту")
    if "social_only" in problems:
        score("social_only", "Лише соцмережі")
    if "website_unreachable" in problems:
        score("website_unreachable", "Сайт не працює")
    if "no_menu" in problems:
        score("no_menu", "Немає онлайн-меню / каталогу")
    if "no_booking" in problems or "no_reservation" in problems:
        score("no_booking", "Немає онлайн-запису / бронювання")
    if "outdated_website" in problems:
        score("outdated_website", "Застарілий сайт")
    if "website_improvable" in problems:
        score("website_improvable", "Сайт можна покращити")
    if "incomplete_info" in problems:
        score("incomplete_info", "Неповна інформація")
    if b.get("category") in HIGH_VALUE:
        score("high_value_niche", "Ніша з високим чеком")
    rating, reviews = b.get("rating"), b.get("reviews_count")
    if rating is not None and reviews is not None and rating >= 4.0 and reviews >= 30:
        score("popular_business", f"Популярний бізнес ({rating}★, {reviews} відгуків)")
    if contact_verified:
        score("has_contact", "Є доступний телефон або email")
    total = max(0, min(100, sum(x["points"] for x in breakdown)))
    tier = "high" if total >= thr.get("high", 70) else "medium" if total >= thr.get("medium", 40) else "low"

    services = recommend_services(problems, offer_kind, booking_kind, cat.group if cat else "services")
    summary = build_summary(b, cat.noun if cat else "Бізнес", website_status, menu_status, booking_status, outdated_status, offer_kind, booking_kind, wa)
    recommendation = build_recommendation(problems, services, cat.group if cat else "services")

    return {
        "website_status": website_status,
        "menu_status": menu_status,
        "booking_status": booking_status,
        "outdated_status": outdated_status,
        "problems": problems,
        "problem_details": details,
        "lead_score": total,
        "lead_tier": tier,
        "score_breakdown": breakdown,
        "contact_verified": contact_verified,
        "phone_norm": phone_e164,
        "recommended_services": services,
        "summary": summary,
        "recommendation": recommendation,
    }


def recommend_services(problems: list[str], offer_kind: str, booking_kind: str, group: str) -> list[str]:
    s: list[str] = []
    if "no_website" in problems or "website_unreachable" in problems:
        if group == "shop" or offer_kind == "catalog":
            s.append("Інтернет-магазин або сайт-каталог товарів")
        elif group == "food":
            s.append("Сучасний сайт закладу з онлайн-меню та кнопкою замовлення")
        elif group == "hotel":
            s.append("Сайт готелю з фотогалереєю та модулем бронювання")
        elif group == "construction":
            s.append("Сайт-портфоліо з прикладами робіт і формою заявки")
        else:
            s.append("Сайт-візитка з послугами, цінами та контактами")
    if "social_only" in problems and s:
        s[0] += ", інтегрований з Instagram/Facebook"
    if "no_menu" in problems:
        s.append("Цифрове QR-меню" if offer_kind == "menu" else "Онлайн-каталог товарів із цінами")
    if "no_booking" in problems:
        s.append("Система онлайн-запису з календарем і нагадуваннями")
    if "no_reservation" in problems:
        s.append("Онлайн-бронювання столиків" if group == "food" else "Модуль онлайн-бронювання номерів")
    if "outdated_website" in problems:
        s.append("Редизайн сайту з мобільною адаптацією та HTTPS")
    if "website_improvable" in problems:
        s.append("Аудит і доопрацювання сайту (SEO, мобільна версія, конверсія)")
    if "incomplete_info" in problems:
        s.append("Оформлення профілів у Google Maps та довідниках")
    return list(dict.fromkeys(s))


def display_name(name: str, noun: str) -> str:
    """«Кав'ярня «Зерно»» → Кав'ярня «Зерно»; «Олена» (перукарня) → Перукарня «Олена»."""
    stem = noun.lower()[:5]
    if stem and stem in name.lower():
        return name
    return f"{noun} «{name}»"


def build_summary(b, noun, ws, ms, bs, os_, offer_kind, booking_kind, wa) -> str:
    name = b.get("name", "")
    parts = []
    nets = [n.capitalize() for n in ("instagram", "facebook") if b.get(n)]
    if ws == "yes":
        parts.append(f"має власний сайт ({(wa or {}).get('final_url') or b.get('website')})")
    elif ws == "social_only":
        parts.append(f"має сторінку {' та '.join(nets) if nets else 'в соцмережі'}, але не має власного вебсайту")
    elif ws == "no":
        parts.append("не має власного вебсайту і сторінок у соцмережах у відкритих джерелах")
    elif ws == "unreachable":
        parts.append("вказує сайт, але він не відкривається")
    else:
        parts.append("має вказаний сайт, який ще не перевірено")
    if ws == "yes" and nets:
        parts.append(f"веде {' та '.join(nets)}")
    if ms == "no":
        parts.append("не має онлайн-меню" if offer_kind == "menu" else "не має онлайн-каталогу")
    elif ms == "yes":
        parts.append("має онлайн-меню" if offer_kind == "menu" else "має онлайн-каталог")
    if bs == "no":
        parts.append("не має онлайн-бронювання" if booking_kind == "reservation" else "не має онлайн-запису")
    elif bs == "yes":
        parts.append("має онлайн-бронювання" if booking_kind == "reservation" else "має онлайн-запис")
    if os_ == "yes":
        parts.append("сайт має ознаки застарілості")
    if len(parts) > 1:
        body = ", ".join(parts[:-1]) + " та " + parts[-1]
    else:
        body = parts[0]
    text = f"{display_name(name, noun)} {body}."
    return text


def build_recommendation(problems: list[str], services: list[str], group: str) -> str:
    if not problems:
        return "Явних проблем цифрової присутності не виявлено. Можна запропонувати маркетинг або підтримку сайту."
    if not services:
        return "Потрібна ручна перевірка."
    main = services[0]
    rest = services[1:3]
    txt = f"Потенційна можливість — {main[0].lower() + main[1:]}"
    if rest:
        txt += ", а також " + "; ".join(r[0].lower() + r[1:] for r in rest)
    return txt + "."


__all__ = ["evaluate", "split_links", "valid_phone", "valid_email", "PROBLEM_LABELS", "STATUS_LABELS", "normalize_url", "social_url"]

"""Аналіз вебсайту бізнесу: доступність, технічний стан, меню/каталог, онлайн-запис, соцмережі, контакти.

Висновки робляться лише на підставі реально отриманої сторінки. Якщо сторінку отримати не вдалося,
результат позначається як неперевірений або недоступний, але не вигадується.
"""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..config import get_settings
from ..services.http import HttpError, request

SOCIAL_DOMAINS = {
    "instagram": ("instagram.com", "instagr.am"),
    "facebook": ("facebook.com", "fb.com", "fb.me", "m.facebook.com"),
    "telegram": ("t.me", "telegram.me"),
    "viber": ("viber.com", "invite.viber.com", "viber://"),
    "whatsapp": ("wa.me", "whatsapp.com", "api.whatsapp.com"),
    "tiktok": ("tiktok.com",),
    "youtube": ("youtube.com", "youtu.be"),
}
LINK_PAGE_DOMAINS = ("taplink.cc", "taplink.ws", "linktr.ee", "linkin.bio", "lnk.bio", "mssg.me", "hipolink.me", "hipolink.net", "beacons.ai", "msha.ke")
MARKETPLACE_DOMAINS = ("prom.ua", "olx.ua", "rozetka.com.ua", "booking.com", "airbnb.", "tripadvisor.", "glovoapp.com", "bolt.eu", "uklon", "google.com/maps", "goo.gl", "maps.app.goo.gl", "2gis.", "business.site")

BOOKING_PROVIDERS = {
    "booksy": "Booksy", "altegio": "Altegio", "yclients": "YCLIENTS", "dikidi": "DIKIDI", "easyweek": "EasyWeek",
    "fresha.com": "Fresha", "treatwell": "Treatwell", "calendly.com": "Calendly", "setmore": "Setmore",
    "simplybook": "SimplyBook.me", "appointy": "Appointy", "reservio": "Reservio", "cliniccards": "ClinicCards",
    "helsi.me": "Helsi", "doc.ua": "Doc.ua", "likarni.com": "Likarni", "opentable": "OpenTable", "resy.com": "Resy",
    "tablein": "Tablein", "restoplace": "Restoplace", "gettable": "GetTable", "choiceqr": "ChoiceQR",
    "servio": "Servio", "otelms": "OTELMS", "travelline": "TravelLine", "bnovo": "Bnovo", "exely": "Exely",
    "wubook": "WuBook", "cloudbeds": "Cloudbeds", "littlehotelier": "Little Hotelier", "beds24": "Beds24",
    "smoobu": "Smoobu", "hotelsmart": "HotelSmart", "sirvoy": "Sirvoy", "booking-widget": "віджет бронювання",
    "bookingform": "форма бронювання", "uds.app": "UDS", "zapys.online": "zapys.online", "beautypro": "BeautyPro",
    "salonsoft": "SalonSoft", "goodsy": "Goodsy",
}
BOOKING_TEXT = re.compile(
    r"(онлайн[\s-]?запис|записатися\s+онлайн|запис\s+онлайн|записатись\s+онлайн|онлайн[\s-]?бронюван|забронювати\s+(онлайн|столик|номер)|"
    r"бронювання\s+(онлайн|столик|номер)|book\s+(now|online|a\s+table)|reserve\s+(now|a\s+table)|make\s+a\s+reservation|"
    r"онлайн[\s-]?запись|записаться\s+онлайн|забронировать)", re.I)
MENU_TEXT = re.compile(r"(^|\b)(меню|menu|наше меню|карта страв|винна карта|бар[\s-]?карта|страви|блюда|our menu)(\b|$)", re.I)
MENU_PROVIDERS = ("choiceqr", "qr-menu", "qrmenu", "menu.ua", "eda.ua", "menu-online", "menuonline", "foodmenu", "orderfood", "poster.menu", "joinposter", "syrve", "iiko")
CATALOG_TEXT = re.compile(r"(каталог|catalog|товари|продукція|products|магазин|shop|кошик|cart|купити|в кошик|add to cart|оформити замовлення)", re.I)
CATALOG_MARKERS = ("woocommerce", "shopify", "add-to-cart", "add_to_cart", "horoshop", "opencart", "route=product", "prestashop", "magento", "/product/", "/catalog", "/shop", "data-product")
SERVICES_TEXT = re.compile(r"(послуги|прайс|ціни|ціна|вартість|price|services|услуги|цены)", re.I)
PARKED_TEXT = re.compile(r"(domain (is )?for sale|домен продається|домен продается|this domain|under construction|сайт у розробці|сайт в розробці|сайт в разработке|coming soon|скоро відкриття|hosting account suspended|account has been suspended|parked)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
YEAR_RE = re.compile(r"(?:©|&copy;|copyright|\(c\))\s*(?:\d{4}\s*[-–—]\s*)?((?:19|20)\d{2})", re.I)

_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}
_robots_lock = threading.Lock()


def classify_url(url: str | None) -> str | None:
    """Тип посилання: social | linkpage | marketplace | website | None."""
    if not url:
        return None
    u = url.lower()
    for domains in SOCIAL_DOMAINS.values():
        if any(d in u for d in domains):
            return "social"
    if any(d in u for d in LINK_PAGE_DOMAINS):
        return "linkpage"
    if any(d in u for d in MARKETPLACE_DOMAINS):
        return "marketplace"
    return "website"


def social_network_of(url: str) -> str | None:
    u = url.lower()
    for net, domains in SOCIAL_DOMAINS.items():
        if any(d in u for d in domains):
            return net
    return None


def normalize_url(url: str) -> str:
    url = url.strip().split()[0].rstrip(";,")
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    return url


def _robots_allows(url: str) -> bool:
    if not get_settings().respect_robots_txt:
        return True
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    with _robots_lock:
        if base in _robots_cache:
            rp = _robots_cache[base]
        else:
            rp = None
            try:
                r = request("GET", base + "/robots.txt", retries=0, timeout=8)
                if r.status_code == 200 and "text" in r.headers.get("Content-Type", "text"):
                    rp = robotparser.RobotFileParser()
                    rp.parse(r.text.splitlines())
            except HttpError:
                rp = None
            _robots_cache[base] = rp
    if rp is None:
        return True
    ua = get_settings().user_agent
    return rp.can_fetch(ua, url)


def _fetch(url: str, max_bytes: int = 2_500_000):
    t0 = time.monotonic()
    resp = request("GET", url, retries=1, backoff=2, timeout=get_settings().http_timeout, allow_redirects=True, stream=True,
                   retry_statuses=(502, 503, 504))
    content = b""
    for chunk in resp.iter_content(65536):
        content += chunk
        if len(content) > max_bytes:
            break
    resp.close()
    elapsed = time.monotonic() - t0
    enc = resp.encoding if resp.encoding and resp.encoding.lower() != "iso-8859-1" else None
    try:
        text = content.decode(enc or "utf-8", errors="replace")
    except LookupError:
        text = content.decode("utf-8", errors="replace")
    return resp, text, elapsed


def _empty_result(url: str) -> dict:
    return {
        "url": url, "checked": False, "status": "unknown", "final_url": None, "http_status": None, "https": None,
        "response_time": None, "title": None, "has_viewport": None, "copyright_year": None, "generator": None,
        "has_menu": None, "menu_evidence": None, "has_catalog": None, "catalog_evidence": None,
        "has_services": None, "has_booking": None, "booking_evidence": None,
        "socials": {}, "emails": [], "phones": [], "outdated_signals": [], "improvement_signals": [],
        "error": None, "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def analyze_website(url: str) -> dict:
    url = normalize_url(url)
    res = _empty_result(url)
    kind = classify_url(url)
    if kind in ("social", "linkpage"):
        res.update(checked=True, status=kind)
        return res
    if not _robots_allows(url):
        res.update(status="robots_blocked", error="robots.txt забороняє автоматичну перевірку цього сайту")
        return res
    try:
        resp, html, elapsed = _fetch(url)
        if resp.status_code >= 400 and url.startswith("http://"):
            # деякі сайти працюють лише по https
            try:
                resp2, html2, el2 = _fetch("https://" + url[7:])
                if resp2.status_code < 400:
                    resp, html, elapsed = resp2, html2, el2
            except HttpError:
                pass
    except HttpError as e:
        if url.startswith("http://"):
            try:
                resp, html, elapsed = _fetch("https://" + url[7:])
            except HttpError:
                res.update(checked=True, status="unreachable", error=str(e))
                return res
        else:
            res.update(checked=True, status="unreachable", error=str(e))
            return res

    res["http_status"] = resp.status_code
    res["final_url"] = resp.url
    res["response_time"] = round(elapsed, 2)
    res["https"] = resp.url.lower().startswith("https://")
    if resp.status_code >= 400:
        res.update(checked=True, status="unreachable", error=f"Сайт відповідає помилкою HTTP {resp.status_code}")
        return res
    ctype = resp.headers.get("Content-Type", "")
    if "html" not in ctype and "<html" not in html[:2000].lower():
        res.update(checked=True, status="ok", error=f"Сторінка не HTML ({ctype})")
        return res
    final_kind = classify_url(resp.url)
    if final_kind in ("social", "linkpage"):
        res.update(checked=True, status=final_kind)
        return res

    res.update(_analyze_html(html, resp.url))
    res["checked"] = True
    res["status"] = "parked" if res.pop("_parked", False) else "ok"

    # Якщо немає email — подивимось сторінку контактів (одна додаткова сторінка, з дотриманням robots.txt)
    contact_link = res.pop("_contact_link", None)
    if not res["emails"] and contact_link and _robots_allows(contact_link):
        try:
            r2, html2, _ = _fetch(contact_link, max_bytes=1_000_000)
            if r2.status_code < 400:
                extra = _analyze_html(html2, r2.url)
                res["emails"] = extra["emails"]
                res["phones"] = list(dict.fromkeys(res["phones"] + extra["phones"]))
                for k, v in extra["socials"].items():
                    res["socials"].setdefault(k, v)
                for flag in ("has_booking", "has_menu", "has_catalog", "has_services"):
                    if extra.get(flag) and not res.get(flag):
                        res[flag] = True
                        ev = flag.replace("has_", "") + "_evidence"
                        if ev in extra and extra.get(ev):
                            res[ev] = extra[ev]
        except HttpError:
            pass
    _finalize_signals(res, elapsed)
    return res


def _analyze_html(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    low = html.lower()
    out: dict = {}
    out["title"] = (soup.title.string or "").strip()[:200] if soup.title and soup.title.string else None
    out["has_viewport"] = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)}) is not None
    gen = soup.find("meta", attrs={"name": re.compile("^generator$", re.I)})
    out["generator"] = gen.get("content", "")[:100] if gen else None
    out["has_meta_description"] = soup.find("meta", attrs={"name": re.compile("^description$", re.I)}) is not None

    text = soup.get_text(" ", strip=True)
    years = [int(y) for y in YEAR_RE.findall(text)]
    out["copyright_year"] = max(years) if years else None
    out["_parked"] = bool(PARKED_TEXT.search(text[:3000])) and len(text) < 3000

    socials: dict[str, str] = {}
    phones: list[str] = []
    emails: list[str] = []
    menu_ev = catalog_ev = services_ev = booking_ev = None
    contact_link = None
    host = urlparse(base_url).netloc.lower()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        label = a.get_text(" ", strip=True)[:80]
        hl = href.lower()
        if hl.startswith("mailto:"):
            em = hl[7:].split("?")[0].strip()
            if EMAIL_RE.fullmatch(em):
                emails.append(em)
            continue
        if hl.startswith("tel:"):
            ph = re.sub(r"[^\d+]", "", href[4:])
            if len(ph) >= 7:
                phones.append(ph)
            continue
        if hl.startswith("viber:"):
            socials.setdefault("viber", href)
            continue
        net = social_network_of(hl)
        if net and not any(x in hl for x in ("/sharer", "share.php", "/share?", "intent/tweet")):
            socials.setdefault(net, href)
            continue
        full = urljoin(base_url, href)
        for key, name in BOOKING_PROVIDERS.items():
            if key in hl and not booking_ev:
                booking_ev = f"посилання на {name}"
        if not menu_ev and (MENU_TEXT.search(label) or re.search(r"/(menu|menyu|meniu|меню)\b", hl) or any(p in hl for p in MENU_PROVIDERS)):
            menu_ev = f"посилання «{label or href}»"
        if not catalog_ev and (re.search(r"/(catalog|katalog|shop|product|products|tovary|магазин)\b", hl) or (label and re.fullmatch(r"(каталог|catalog|магазин|товари|shop|продукція)", label.strip(), re.I))):
            catalog_ev = f"посилання «{label or href}»"
        if not services_ev and label and SERVICES_TEXT.search(label):
            services_ev = f"посилання «{label}»"
        if not booking_ev and label and BOOKING_TEXT.search(label):
            booking_ev = f"кнопка/посилання «{label}»"
        if not contact_link and urlparse(full).netloc.lower() == host and re.search(r"(contact|kontakt|контакт)", hl + " " + label.lower()):
            contact_link = full

    # вбудовані віджети (iframe/script)
    for tag in soup.find_all(["iframe", "script"], src=True):
        src = tag["src"].lower()
        for key, name in BOOKING_PROVIDERS.items():
            if key in src and not booking_ev:
                booking_ev = f"вбудований віджет {name}"
        if not menu_ev and any(p in src for p in MENU_PROVIDERS):
            menu_ev = "вбудоване онлайн-меню"
    if not booking_ev:
        m = BOOKING_TEXT.search(text)
        if m:
            booking_ev = f"текст «{m.group(0)}»"
    if not catalog_ev and any(mk in low for mk in CATALOG_MARKERS):
        catalog_ev = "ознаки інтернет-магазину в коді сторінки"
    if not menu_ev:
        # меню у вигляді PDF або розділу на сторінці
        for a in soup.find_all("a", href=True):
            if a["href"].lower().endswith(".pdf") and re.search(r"(menu|меню)", (a["href"] + a.get_text()).lower()):
                menu_ev = "меню у форматі PDF"
                break
    if not menu_ev:
        for h in soup.find_all(re.compile("^h[1-4]$")):
            if MENU_TEXT.search(h.get_text(" ", strip=True)[:60]):
                menu_ev = f"розділ «{h.get_text(' ', strip=True)[:60]}»"
                break

    for em in EMAIL_RE.findall(text):
        em = em.lower()
        if not re.search(r"\.(png|jpe?g|gif|svg|webp)$", em) and "example" not in em and "sentry" not in em and "wixpress" not in em:
            emails.append(em)

    out["socials"] = socials
    out["emails"] = list(dict.fromkeys(emails))[:5]
    out["phones"] = list(dict.fromkeys(phones))[:5]
    out["has_menu"] = bool(menu_ev)
    out["menu_evidence"] = menu_ev
    out["has_catalog"] = bool(catalog_ev)
    out["catalog_evidence"] = catalog_ev
    out["has_services"] = bool(services_ev)
    out["services_evidence"] = services_ev
    out["has_booking"] = bool(booking_ev)
    out["booking_evidence"] = booking_ev
    out["_contact_link"] = contact_link

    # технічні ознаки застарілості
    signals = []
    if soup.find(["frameset", "frame"]):
        signals.append(("frames", "Сайт побудований на фреймах (застаріла технологія)", True))
    if ".swf" in low or "application/x-shockwave-flash" in low:
        signals.append(("flash", "Використовується Flash, який не підтримують сучасні браузери", True))
    jq = re.search(r"jquery[.-]?(\d)\.(\d+)(?:\.\d+)?(?:\.min)?\.js", low)
    if jq and (int(jq.group(1)), int(jq.group(2))) < (1, 12):
        signals.append(("old_jquery", f"Стара версія jQuery {jq.group(1)}.{jq.group(2)}", True))
    g = (out["generator"] or "").lower()
    m = re.search(r"wordpress\s+(\d+)", g)
    if m and int(m.group(1)) < 5:
        signals.append(("old_cms", f"Застаріла версія CMS: {out['generator']}", True))
    m = re.search(r"joomla!?\s*(\d+)", g)
    if m and int(m.group(1)) < 3:
        signals.append(("old_cms", f"Застаріла версія CMS: {out['generator']}", True))
    m = re.search(r"drupal\s+(\d+)", g)
    if m and int(m.group(1)) < 8:
        signals.append(("old_cms", f"Застаріла версія CMS: {out['generator']}", True))
    if "ucoz" in low or "narod.ru" in low:
        signals.append(("old_builder", "Сайт на застарілому безкоштовному конструкторі (uCoz/narod)", True))
    head = html[:300].lower()
    if "html 4.01" in head or "xhtml 1.0 transitional" in head:
        signals.append(("old_html", "Застарілий стандарт розмітки (HTML 4 / XHTML)", False))
    if len(soup.find_all(["font", "marquee", "center"])) >= 5:
        signals.append(("old_markup", "Застарілі HTML-теги оформлення (font/center/marquee)", False))
    out["_signals"] = signals
    return out


def _finalize_signals(res: dict, elapsed: float) -> None:
    signals = res.pop("_signals", [])
    if res.get("status") == "parked":
        signals.append(("parked", "Сайт-заглушка: «у розробці» / домен припаркований", True))
    if res.get("https") is False:
        signals.append(("no_https", "Немає HTTPS — браузери позначають сайт як «Не захищений»", False))
    if res.get("has_viewport") is False:
        signals.append(("no_viewport", "Сайт не адаптований для мобільних (немає meta viewport)", False))
    year = res.get("copyright_year")
    if year and year <= datetime.now(timezone.utc).year - 3:
        signals.append(("old_copyright", f"Останній рік у футері — {year}, сайт давно не оновлювався", False))
    if elapsed and elapsed > 5:
        signals.append(("slow", f"Повільне завантаження головної сторінки ({elapsed:.1f} с)", False))
    res["outdated_signals"] = [{"code": c, "text": t, "strong": s} for c, t, s in signals]
    strong = any(s for _, _, s in signals)
    weak = sum(1 for _, _, s in signals if not s)
    res["is_outdated"] = strong or weak >= 2
    improvements = []
    if not res.get("has_meta_description"):
        improvements.append("Немає meta description (слабке SEO)")
    if not res.get("title"):
        improvements.append("Немає заголовка сторінки (title)")
    if not res.get("socials"):
        improvements.append("На сайті немає посилань на соцмережі чи месенджери")
    if not res.get("phones") and not res.get("emails"):
        improvements.append("На головній сторінці немає клікабельного телефону чи email")
    res["improvement_signals"] = improvements

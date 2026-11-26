from app.analysis.evaluate import evaluate, split_links, valid_phone
from app.analysis.website import classify_url
from app.categories import classify_osm_tags
from app.services.dedup import normalize_address, normalize_name, similar
from app.services.settings_store import DEFAULTS
from app.sources.base import SearchArea
from app.sources.osm import build_query

SC = DEFAULTS["scoring"]


def test_phone_validation():
    assert valid_phone("+380 67 111 2233") == "+380671112233"
    assert valid_phone("067 111 22 33") == "+380671112233"
    assert valid_phone("123") is None


def test_classify():
    assert classify_url("https://instagram.com/x") == "social"
    assert classify_url("https://taplink.cc/x") == "linkpage"
    assert classify_url("https://mycafe.ua") == "website"
    assert classify_osm_tags({"amenity": "cafe"}) == "cafe"
    assert classify_osm_tags({"shop": "hairdresser"}) == "hairdresser"
    assert classify_osm_tags({"craft": "plumber"}) == "construction"


def test_normalize():
    assert normalize_name('Кав\'ярня «Зерно»') == "зерно"
    assert similar(normalize_name('Перукарня "Олена"'), normalize_name("Перукарня Олена")) == 1.0
    assert normalize_address("вул. Шевченка, 5") == normalize_address("вулиця Шевченка 5")


def test_social_only_scoring():
    b = {"name": "Зерно", "category": "cafe", "website": "https://instagram.com/zerno", "phone": "+380671112233", "address": "x"}
    split_links(b)
    assert b["website"] is None and b["instagram"]
    ev = evaluate(b, None, SC)
    assert ev["website_status"] == "social_only"
    assert {"no_website", "social_only", "no_menu"} <= set(ev["problems"])
    assert "no_reservation" not in ev["problems"]  # для кав'ярні бронювання не вимагається
    # 30 (немає сайту) + 15 (лише соцмережі) + 20 (немає меню) + 10 (є контакт)
    assert ev["lead_score"] == 75
    assert ev["lead_tier"] == "high"


def test_unverified_website_is_not_problem():
    b = {"name": "X", "category": "cafe", "website": "https://x.ua", "phone": None}
    ev = evaluate(b, None, SC)  # сайт не перевірявся
    assert ev["website_status"] == "unknown"
    assert ev["menu_status"] == "unknown"
    assert "no_website" not in ev["problems"] and "no_menu" not in ev["problems"]


def test_overpass_query():
    q = build_query(SearchArea(label="x", lat=1, lon=2, osm_area_id=3600000001), ["cafe", "dentist"], 100)
    assert 'area(3600000001)->.searchArea' in q and '"amenity"="cafe"' in q and '"amenity"="dentist"' in q
    q2 = build_query(SearchArea(label="x", lat=49.8, lon=24.0, radius_m=2000), ["bar"], 50)
    assert "around:2000,49.800000,24.000000" in q2 and "out center tags 50" in q2


def test_html_detection():
    from app.analysis.website import _analyze_html, _finalize_signals
    from tests.fake_servers import MODERN, OLD

    m = _analyze_html(MODERN, "https://modern.ua/")
    assert m["has_menu"] and m["has_booking"] and "Booksy" in m["booking_evidence"]
    assert m["socials"]["instagram"].startswith("https://instagram.com")
    assert m["phones"] == ["+380671234567"] and m["has_viewport"]
    o = _analyze_html(OLD, "http://old.ua/")
    res = {**o, "https": False}
    _finalize_signals(res, 1.0)
    codes = {s["code"] for s in res["outdated_signals"]}
    assert {"old_cms", "old_jquery", "no_https", "no_viewport", "old_copyright"} <= codes
    assert res["is_outdated"]

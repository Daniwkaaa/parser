"""Наскрізний сценарій через API: пошук → аналіз → дедуплікація → збереження → фільтри → експорт → нотатки."""
import io
import time

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import app
from tests import fake_servers


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def wait_job(client, jid, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{jid}").json()
        if j["status"] not in ("running", "queued"):
            return j
        time.sleep(0.3)
    raise AssertionError("job timeout")


SEARCH = {"country": "Україна", "city": "Львів", "categories": ["cafe", "hairdresser", "tyres", "dentist", "fast_food"],
          "limit": 50, "comprehensive": True, "sources": ["osm"], "check_websites": True, "exclude_chains": True}


def by_name(client):
    items = client.get("/api/businesses?page_size=100").json()["items"]
    return {b["name"]: b for b in items}


def test_full_flow(client):
    r = client.post("/api/search", json=SEARCH)
    assert r.status_code == 200, r.text
    job = wait_job(client, r.json()["id"])
    assert job["status"] == "completed", job
    assert "area(3602032280)" in fake_servers.STATE["last_query"]
    assert job["found_count"] == 6  # без назви — пропущено; McDonald's — виключено як мережа
    assert job["saved_count"] == 6
    assert job["new_count"] == 5 and job["duplicate_count"] == 1  # дубль перукарні об'єднано

    logs = client.get(f"/api/jobs/{job['id']}/logs").json()
    assert any("Готово" in l["message"] for l in logs)

    m = by_name(client)
    assert len(m) == 5
    zerno = m["Кав'ярня «Зерно»"]
    assert zerno["website_status"] == "social_only" and zerno["instagram"]
    assert zerno["menu_status"] == "no"
    assert "social_only" in zerno["problems"] and zerno["lead_tier"] == "high"

    modern = m["Кафе Модерн"]
    assert modern["website_status"] == "yes"
    assert modern["menu_status"] == "yes" and modern["booking_status"] == "na"  # для кав'ярні запис не застосовується
    assert modern["outdated_status"] == "no"
    assert "no_website" not in modern["problems"]
    assert modern["lead_score"] < zerno["lead_score"]

    old = m["Шиномонтаж Колесо"]
    assert old["outdated_status"] == "yes" and "outdated_website" in old["problems"]
    detail = client.get(f"/api/businesses/{old['id']}").json()
    assert detail["email"] == "info@oldtyre.ua"  # знайдено на сторінці контактів
    assert any(s["code"] == "old_cms" for s in detail["website_analysis"]["outdated_signals"])

    dent = m["Стоматологія Посмішка"]
    assert dent["website_status"] == "unreachable" and "website_unreachable" in dent["problems"]

    hair = m["Перукарня Олена"]
    hd = client.get(f"/api/businesses/{hair['id']}").json()
    assert hd["website_status"] == "no" and "no_booking" in hd["problems"]
    assert len(hd["sources_full"]) == 2 and hd["opening_hours"]  # дані дубля злито
    assert hd["contact_verified"] is True
    assert "McDonald's" not in m and "Мережа Кава Плюс" not in m
    assert any("Мережа Кава Плюс" in l["message"] for l in logs)


def test_dedup_on_repeat_search(client):
    before = client.get("/api/businesses").json()["total"]
    r = client.post("/api/search", json=SEARCH)
    job = wait_job(client, r.json()["id"])
    assert job["new_count"] == 0 and job["duplicate_count"] == 6
    assert client.get("/api/businesses").json()["total"] == before


def test_filters_and_search(client):
    r = client.get("/api/businesses?problems=no_website").json()
    names = {b["name"] for b in r["items"]}
    assert names == {"Кав'ярня «Зерно»", "Перукарня Олена"}
    r = client.get("/api/businesses?problems=outdated_website").json()
    assert [b["name"] for b in r["items"]] == ["Шиномонтаж Колесо"]
    r = client.get("/api/businesses?q=0501112233").json()
    assert r["items"][0]["name"] == "Перукарня Олена"
    r = client.get("/api/businesses?q=шевченка").json()
    assert r["total"] == 1
    r = client.get("/api/businesses?categories=cafe&sort=lead_score&order=desc").json()
    assert [b["name"] for b in r["items"]][0] == "Кав'ярня «Зерно»"
    assert client.get("/api/businesses?tiers=high").json()["total"] >= 1


def test_problem_filtered_search(client):
    """Пошук лише за проблемою «Застарілий сайт» — зберігаються тільки відповідні."""
    body = {**SEARCH, "comprehensive": False, "problems": ["outdated_website"]}
    job = wait_job(client, client.post("/api/search", json=body).json()["id"])
    assert job["saved_count"] == 1
    res = client.get(f"/api/businesses?job_id={job['id']}").json()
    assert [b["name"] for b in res["items"]] == ["Шиномонтаж Колесо"]


def test_status_notes_recheck(client):
    bid = by_name(client)["Кафе Модерн"]["id"]
    assert client.patch(f"/api/businesses/{bid}", json={"status": "contacted"}).json()["status"] == "contacted"
    assert client.patch(f"/api/businesses/{bid}", json={"status": "bogus"}).status_code == 422
    d = client.post(f"/api/businesses/{bid}/notes", json={"text": "Подзвонити в понеділок"}).json()
    assert d["notes"][0]["text"] == "Подзвонити в понеділок"
    assert client.delete(f"/api/businesses/{bid}/notes/{d['notes'][0]['id']}").json()["ok"]
    d = client.post(f"/api/businesses/{bid}/recheck").json()
    assert d["website_status"] == "yes" and d["last_checked_at"]


def test_scoring_settings(client):
    s = client.get("/api/settings").json()
    w = s["scoring"]["weights"]
    w["no_website"] = 50
    r = client.put("/api/settings/scoring", json={"weights": w, "thresholds": {"high": 70, "medium": 40}}).json()
    assert r["rescored"] >= 5
    hair = by_name(client)["Перукарня Олена"]
    assert hair["lead_score"] == min(100, 50 + 10 + 10 + 5)  # + ніша з високим чеком
    client.post("/api/settings/reset-scoring")
    assert by_name(client)["Перукарня Олена"]["lead_score"] == 30 + 10 + 10 + 5
    bad = client.put("/api/settings/scoring", json={"weights": w, "thresholds": {"high": 30, "medium": 40}})
    assert bad.status_code == 400


def test_api_keys_masked(client):
    client.put("/api/settings/api-keys", json={"serpapi": "abcd1234567890xyz"})
    k = client.get("/api/settings").json()["api_keys"]["serpapi"]
    assert k["configured"] and "1234567890" not in k["masked"]


def test_export(client):
    csv = client.get("/api/export?format=csv")
    assert csv.status_code == 200
    text = csv.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Назва;Категорія;Lead Score")
    assert "Кав'ярня «Зерно»" in text and len(text.strip().splitlines()) == 6
    x = client.get("/api/export?format=xlsx&problems=no_website")
    wb = load_workbook(io.BytesIO(x.content))
    ws = wb.active
    assert ws.max_row == 3 and ws["A1"].value == "Назва"


def test_stats_and_map(client):
    s = client.get("/api/stats").json()
    assert s["totals"]["businesses"] == 5
    assert s["totals"]["no_website"] == 2
    assert s["totals"]["verified_contacts"] >= 3
    pts = client.get("/api/businesses/map").json()
    assert len(pts) == 5 and all(p["lat"] for p in pts)


def test_bad_location(client):
    r = client.post("/api/search", json={**SEARCH, "city": "Nowhere"})
    job = wait_job(client, r.json()["id"])
    assert job["status"] == "failed" and "не знайдено" in job["error"]


def test_validation(client):
    assert client.post("/api/search", json={**SEARCH, "categories": []}).status_code == 422
    assert client.post("/api/search", json={**SEARCH, "categories": ["nope"]}).status_code == 422


def test_resume_interrupted(client):
    from app.db import SessionLocal
    from app.models import SearchJob
    from app.services.jobs import recover_interrupted

    db = SessionLocal()
    j = SearchJob(params={**SEARCH}, status="running", stage="analyze")
    db.add(j); db.commit(); jid = j.id; db.close()
    recover_interrupted()
    assert client.get(f"/api/jobs/{jid}").json()["status"] == "interrupted"
    client.post(f"/api/jobs/{jid}/resume")
    assert wait_job(client, jid)["status"] == "completed"


def test_limit_does_not_leave_extra_records(client):
    """Записи понад ліміт (паралельна обробка) не залишаються в базі."""
    for b in client.get("/api/businesses?page_size=100").json()["items"]:
        client.delete(f"/api/businesses/{b['id']}")
    job = wait_job(client, client.post("/api/search", json={**SEARCH, "limit": 2}).json()["id"])
    assert job["saved_count"] == 2
    assert client.get("/api/businesses").json()["total"] == 2
    assert client.get(f"/api/businesses?job_id={job['id']}").json()["total"] == 2

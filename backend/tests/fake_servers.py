"""Локальні тестові сервери (лише для автотестів): імітація Overpass/Nominatim і кількох сайтів.

Ці дані ніколи не потрапляють у робочу базу — тести використовують тимчасову БД.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATE = {"overpass_calls": 0, "port": 0}

MODERN = """<!doctype html><html><head><meta name="viewport" content="width=device-width"><title>Кафе Модерн</title>
<meta name="description" content="Найкраща кава"></head><body>
<nav><a href="/menu">Меню</a><a href="https://booksy.com/x">Записатися</a><a href="/contacts">Контакти</a></nav>
<a href="https://instagram.com/modern_cafe">Instagram</a><a href="tel:+380671234567">Подзвонити</a>
<footer>© 2025 Modern</footer></body></html>"""

OLD = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"><html><head><title>Шиномонтаж</title>
<meta name="generator" content="Joomla! 1.5 - Open Source Content Management">
<script src="/js/jquery-1.4.2.min.js"></script></head><body><center><font>Ласкаво просимо</font></center>
<font>Шиномонтаж</font><font>a</font><font>b</font><font>c</font><a href="/contacts">Контакти</a>
<p>Copyright © 2014</p></body></html>"""

CONTACTS = """<html><body>Пишіть нам: info@oldtyre.ua <a href="mailto:info@oldtyre.ua">email</a></body></html>"""


def overpass_payload(port: int) -> dict:
    base = f"http://127.0.0.1:{port}"
    return {"elements": [
        # кав'ярня лише з Instagram (через поле website) — має бути «лише соцмережі»
        {"type": "node", "id": 1, "lat": 49.8400, "lon": 24.0300, "tags": {
            "amenity": "cafe", "name": "Кав'ярня «Зерно»", "phone": "+380 67 111 2233",
            "website": "https://www.instagram.com/zerno_lviv/", "addr:street": "вулиця Шевченка", "addr:housenumber": "5"}},
        # кафе з сучасним сайтом, меню і записом
        {"type": "node", "id": 2, "lat": 49.8410, "lon": 24.0310, "tags": {
            "amenity": "cafe", "name": "Кафе Модерн", "website": f"{base}/modern", "opening_hours": "Mo-Su 08:00-22:00",
            "addr:street": "площа Ринок", "addr:housenumber": "1", "contact:phone": "+380 67 123 4567"}},
        # шиномонтаж із застарілим сайтом
        {"type": "way", "id": 3, "center": {"lat": 49.8500, "lon": 24.0400}, "tags": {
            "shop": "tyres", "name": "Шиномонтаж Колесо", "website": f"{base}/old", "phone": "0322 555 666"}},
        # салон краси без сайту і соцмереж
        {"type": "node", "id": 4, "lat": 49.8420, "lon": 24.0320, "tags": {
            "shop": "hairdresser", "name": "Перукарня Олена", "phone": "+380501112233", "addr:street": "вулиця Городоцька", "addr:housenumber": "10"}},
        # сайт не працює
        {"type": "node", "id": 5, "lat": 49.8430, "lon": 24.0330, "tags": {
            "amenity": "dentist", "name": "Стоматологія Посмішка", "website": f"{base}/down", "email": "dent@example.ua"}},
        # дубль перукарні з іншим ID (той самий телефон, поруч)
        {"type": "node", "id": 6, "lat": 49.84205, "lon": 24.03205, "tags": {
            "shop": "hairdresser", "name": "Перукарня \"Олена\"", "phone": "050 111 22 33", "opening_hours": "Mo-Fr 09:00-19:00"}},
        # мережа — має бути виключена
        {"type": "node", "id": 7, "lat": 49.8440, "lon": 24.0340, "tags": {
            "amenity": "fast_food", "name": "McDonald's", "brand": "McDonald's", "brand:wikidata": "Q38076"}},
        # без назви — пропускається
        {"type": "node", "id": 8, "lat": 49.8, "lon": 24.0, "tags": {"amenity": "cafe"}},
    ]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # тихо
        pass

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/search":
            q = parse_qs(p.query)
            if "Nowhere" in (q.get("city", [""])[0] + q.get("q", [""])[0]):
                return self._send(200, "[]", "application/json")
            return self._send(200, json.dumps([{"osm_type": "relation", "osm_id": 2032280, "lat": "49.8419", "lon": "24.0315",
                                                "display_name": "Львів, Львівська область, Україна",
                                                "boundingbox": ["49.77", "49.90", "23.90", "24.13"],
                                                "address": {"city": "Львів", "state": "Львівська область", "country": "Україна", "country_code": "ua"}}]),
                              "application/json")
        if p.path == "/robots.txt":
            return self._send(200, "User-agent: *\nDisallow: /private\n", "text/plain")
        if p.path == "/modern":
            return self._send(200, MODERN)
        if p.path == "/old":
            return self._send(200, OLD)
        if p.path == "/contacts":
            return self._send(200, CONTACTS)
        if p.path == "/menu":
            return self._send(200, "<html><body><h1>Меню</h1></body></html>")
        if p.path == "/down":
            return self._send(500, "Internal error")
        return self._send(404, "not found")

    def do_POST(self):
        if self.path.startswith("/api/interpreter"):
            STATE["overpass_calls"] += 1
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            STATE["last_query"] = parse_qs(body).get("data", [""])[0]
            return self._send(200, json.dumps(overpass_payload(STATE["port"])), "application/json")
        return self._send(404, "")


def start() -> int:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    STATE["port"] = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return STATE["port"]

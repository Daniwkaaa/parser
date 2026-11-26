"""Запуск сервера LeadFinder: python run.py  →  http://127.0.0.1:8000"""
import os
import sys
import threading
import webbrowser

import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    if "--no-browser" not in sys.argv:
        threading.Timer(2.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("app.main:app", host=host, port=port, reload="--reload" in sys.argv)

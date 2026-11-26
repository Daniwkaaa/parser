#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Потрібен Python 3.10+"; exit 1; }
[ -x backend/.venv/bin/python ] || python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -q --disable-pip-version-check -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
if command -v npm >/dev/null; then
  (cd frontend && npm install --no-audit --no-fund --loglevel=error && npm run build --silent)
elif [ ! -f frontend/dist/index.html ]; then
  echo "Потрібен Node.js 18+ (https://nodejs.org)"; exit 1
fi
cd backend && exec .venv/bin/python run.py "$@"

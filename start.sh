#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Потрібен Python 3.10+"; exit 1; }
[ -x backend/.venv/bin/python ] || python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -q --disable-pip-version-check -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null || { echo "Потрібен Node.js 18+ (https://nodejs.org)"; exit 1; }
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi
cd backend && exec .venv/bin/python run.py "$@"

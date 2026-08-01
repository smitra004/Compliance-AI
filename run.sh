#!/usr/bin/env bash
# One-shot local dev launcher (no Docker). Ctrl-C stops both.
set -e
( cd backend && python3 -m venv venv 2>/dev/null || true
  source venv/bin/activate && pip install -q -r requirements.txt
  uvicorn app.main:app --reload --port 8010 ) &
BE=$!
( cd frontend && npm install --silent && npm run dev ) &
FE=$!
trap "kill $BE $FE 2>/dev/null" EXIT
wait

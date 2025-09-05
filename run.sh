#!/usr/bin/env bash
source .venv/bin/activate || true
uvicorn app.main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000}

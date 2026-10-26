#!/usr/bin/env bash
# 单独启动后端（配合 scripts/dev-frontend.sh 使用）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

"$ROOT_DIR/scripts/setup.sh" >/dev/null

docker compose up -d db redis

cd backend
exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

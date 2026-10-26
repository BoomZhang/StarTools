#!/usr/bin/env bash
# 构建并启动完整服务（前端 + 后端 + PostgreSQL + Redis + Nginx）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

[[ -f .env ]] || cp .env.example .env

if [[ ! -s backend/models/whisper/base/model.bin ]]; then
  "$ROOT_DIR/scripts/fetch-models.sh"
fi

APP_PORT="$(grep -E '^APP_PORT=' .env | tail -n 1 | cut -d '=' -f 2 || true)"
APP_PORT="${APP_PORT:-8080}"

docker compose up -d --build
docker compose ps

echo
echo "[up] 前端：http://127.0.0.1:${APP_PORT}/startools/"
echo "[up] 接口文档：http://127.0.0.1:${APP_PORT}/api/docs"

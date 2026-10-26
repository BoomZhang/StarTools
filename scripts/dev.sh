#!/usr/bin/env bash
# 一键启动本机开发环境：中间件容器 + FastAPI + Vite
# 用法：./scripts/dev.sh   （Ctrl+C 一起退出）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[dev] 未找到 docker，请先安装并启动 Docker" >&2
  exit 1
fi

"$ROOT_DIR/scripts/setup.sh"

echo "[dev] 启动 PostgreSQL 与 Redis 容器..."
docker compose up -d db redis

echo "[dev] 等待 PostgreSQL 就绪..."
for _ in $(seq 1 30); do
  if docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    echo "[dev] PostgreSQL 已就绪"
    break
  fi
  sleep 1
done

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "[dev] 后端启动中：http://127.0.0.1:8000/api/docs"
(
  cd backend
  .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

echo "[dev] 前端启动中：http://127.0.0.1:5173/startools/"
(
  cd frontend
  npm run dev
)

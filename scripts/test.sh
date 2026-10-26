#!/usr/bin/env bash
# 本地校验：后端单元测试 + 前端类型检查与构建
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

"$ROOT_DIR/scripts/setup.sh" >/dev/null

echo "[test] 启动测试依赖..."
docker compose up -d db redis >/dev/null
for _ in $(seq 1 30); do
  if docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[test] 运行后端测试..."
(cd backend && .venv/bin/python -m pytest -q)

echo "[test] 构建前端..."
(cd frontend && npm run build)

echo "[test] 全部通过"

#!/usr/bin/env bash
# 单独启动前端（配合 scripts/dev-backend.sh 使用）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

[[ -f .env ]] || cp .env.example .env

if [[ ! -d node_modules ]]; then
  echo "[dev-frontend] 首次运行，安装依赖..."
  npm install
fi

exec npm run dev

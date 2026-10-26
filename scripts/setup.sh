#!/usr/bin/env bash
# 准备本机开发环境：生成 env 文件、安装后端与前端依赖
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

[[ -f .env ]] || cp .env.example .env
[[ -f backend/.env ]] || cp backend/.env.example backend/.env
[[ -f frontend/.env ]] || cp frontend/.env.example frontend/.env

if [[ ! -d backend/.venv ]]; then
  echo "[setup] 创建 Python 虚拟环境..."
  python3 -m venv backend/.venv
fi

echo "[setup] 安装后端依赖..."
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements-dev.txt

if [[ ! -s backend/models/whisper/base/model.bin ]]; then
  "$ROOT_DIR/scripts/fetch-models.sh"
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "[setup] 安装前端依赖..."
  if [[ -f frontend/package-lock.json ]]; then
    (cd frontend && npm ci)
  else
    (cd frontend && npm install)
  fi
fi

echo "[setup] 依赖准备完成"

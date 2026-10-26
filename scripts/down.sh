#!/usr/bin/env bash
# 停止服务；加 --volumes 同时删除数据库/Redis 数据卷
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose down "$@"

#!/usr/bin/env bash
# 在 Apple Silicon Mac 上构建极空间 x86 NAS 可导入的镜像包
#
# 用法：
#   ./scripts/build-nas-package.sh
#   NAS_URL=http://192.168.1.10:8080 ./scripts/build-nas-package.sh
#   MIRRORS="docker.1ms.run docker.1panel.live" ./scripts/build-nas-package.sh
#   TARGET_PLATFORM=linux/arm64 ./scripts/build-nas-package.sh   # 仅 ARM NAS 使用
#
# 产物（每个镜像单独一个包，便于极空间逐个导入）：
#   dist-nas/docker-compose.yml
#   dist-nas/startools-backend.tar.gz
#   dist-nas/startools-frontend.tar.gz
#   dist-nas/postgres-16-alpine.tar.gz
#   dist-nas/redis-7-alpine.tar.gz
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist-nas}"
TARGET_PLATFORM="${TARGET_PLATFORM:-linux/amd64}"
EXPECTED_ARCH="${TARGET_PLATFORM#linux/}"
NAS_PORT="${NAS_PORT:-8080}"
# 默认让 CORS 地址与前端宿主机端口保持一致
NAS_URL="${NAS_URL:-http://localhost:${NAS_PORT}}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
MIRRORS="${MIRRORS:-docker.m.daocloud.io docker.1ms.run docker.1panel.live}"
PULL_RETRIES="${PULL_RETRIES:-3}"

say() {
  printf '\n[%s] %s\n' "$1" "$2"
}

fail() {
  printf '\n错误：%s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
command -v curl >/dev/null 2>&1 || fail "未找到 curl 命令"
command -v openssl >/dev/null 2>&1 || fail "未找到 openssl 命令"

docker info >/dev/null 2>&1 || fail "Docker Desktop 未启动，请先打开 Docker Desktop 并等待引擎就绪"
docker compose version >/dev/null 2>&1 || fail "当前 Docker 不支持 docker compose，请升级 Docker Desktop"

case "$NAS_URL" in
  https://*) COOKIE_SECURE="true" ;;
  *) COOKIE_SECURE="false" ;;
esac

say "环境" "主机 $(uname -m)，目标平台 ${TARGET_PLATFORM}，镜像源 ${MIRRORS}"

if [ ! -s backend/models/whisper/base/model.bin ]; then
  say "模型" "未找到 Whisper 模型，开始下载（约 141MB）"
  if ! scripts/fetch-models.sh; then
    fail "Whisper 模型下载失败。请检查网络，或从其他机器复制 backend/models/whisper/base 后重试"
  fi
fi

mirror_reachable() {
  local mirror="$1"
  local code
  code="$(curl -s -o /dev/null -m 8 -w '%{http_code}' "https://${mirror}/v2/" || true)"
  case "$code" in
    200|401|403) return 0 ;;
    *) return 1 ;;
  esac
}

# 从国内镜像源拉取镜像，并打回 Docker 官方标准 tag。
# 输出选中镜像的完整引用，供 Dockerfile 的 FROM 使用。
# 注意：Docker Desktop 的 containerd 镜像仓库里，官方镜像 tag 可能指向多架构索引，
# 因此这里不校验 .Architecture，交给 --platform 和构建阶段选择正确架构。
pick_image() {
  local ref="$1"
  local standard="$2"
  local mirror
  local full
  local attempt

  for mirror in $MIRRORS; do
    full="${mirror}/${ref}"
    if ! mirror_reachable "$mirror"; then
      printf '[skip] %s 不可达\n' "$mirror" >&2
      continue
    fi
    attempt=1
    while [ "$attempt" -le "$PULL_RETRIES" ]; do
      printf '[pull] %s (%s)，第 %s/%s 次\n' "$full" "$TARGET_PLATFORM" "$attempt" "$PULL_RETRIES" >&2
      if docker pull --platform "$TARGET_PLATFORM" "$full" >/dev/null 2>&1; then
        docker tag "$full" "$standard" >/dev/null 2>&1 || true
        printf '%s' "$full"
        return 0
      fi
      printf '[warn] %s 拉取失败，重试或切换镜像源\n' "$mirror" >&2
      attempt=$((attempt + 1))
      sleep 2
    done
  done
  return 1
}

say "基础镜像" "拉取 python / node / nginx"
PY_BASE="$(pick_image 'library/python:3.12-slim' 'python:3.12-slim')" || \
  fail "python:3.12-slim 拉取失败。可设置 MIRRORS=\"docker.1ms.run docker.1panel.live\" 后重试"
NODE_BASE="$(pick_image 'library/node:22-alpine' 'node:22-alpine')" || \
  fail "node:22-alpine 拉取失败。可设置 MIRRORS=\"docker.1ms.run docker.1panel.live\" 后重试"
NGINX_BASE="$(pick_image 'library/nginx:1.27-alpine' 'nginx:1.27-alpine')" || \
  fail "nginx:1.27-alpine 拉取失败。可设置 MIRRORS=\"docker.1ms.run docker.1panel.live\" 后重试"

say "NAS 基础服务" "拉取 postgres / redis"
POSTGRES_BASE="$(pick_image 'library/postgres:16-alpine' 'postgres:16-alpine')" || \
  fail "postgres:16-alpine 拉取失败。可设置 MIRRORS=\"docker.1ms.run docker.1panel.live\" 后重试"
REDIS_BASE="$(pick_image 'library/redis:7-alpine' 'redis:7-alpine')" || \
  fail "redis:7-alpine 拉取失败。可设置 MIRRORS=\"docker.1ms.run docker.1panel.live\" 后重试"

say "构建" "startools-backend + startools-frontend（${TARGET_PLATFORM}）"
say "提示" "M4 构建 amd64 会经过模拟，后端包含 LibreOffice/Tesseract，耗时会明显长于原生构建"
if ! PYTHON_IMAGE="$PY_BASE" \
     NODE_IMAGE="$NODE_BASE" \
     NGINX_IMAGE="$NGINX_BASE" \
     DOCKER_DEFAULT_PLATFORM="$TARGET_PLATFORM" \
     docker compose build backend frontend; then
  fail "镜像构建失败。请把最后一段报错发出来，或尝试更换 MIRRORS"
fi

verify_arch() {
  local image="$1"
  local arch
  arch="$(docker image inspect "$image" --format '{{.Architecture}}' 2>/dev/null || true)"
  [ "$arch" = "$EXPECTED_ARCH" ] || fail "$image 架构为 ${arch:-unknown}，预期 ${EXPECTED_ARCH}"
}

say "校验" "确认自建镜像架构"
verify_arch "startools-backend:latest"
verify_arch "startools-frontend:latest"

mkdir -p "$DIST_DIR"

# 极空间的镜像导入一次只处理一个镜像，因此按镜像分别导出
say "导出" "startools-backend.tar.gz"
docker save --platform "$TARGET_PLATFORM" startools-backend:latest \
  | gzip > "$DIST_DIR/startools-backend.tar.gz"

say "导出" "startools-frontend.tar.gz"
docker save --platform "$TARGET_PLATFORM" startools-frontend:latest \
  | gzip > "$DIST_DIR/startools-frontend.tar.gz"

say "导出" "postgres-16-alpine.tar.gz"
docker save --platform "$TARGET_PLATFORM" postgres:16-alpine \
  | gzip > "$DIST_DIR/postgres-16-alpine.tar.gz"

say "导出" "redis-7-alpine.tar.gz"
docker save --platform "$TARGET_PLATFORM" redis:7-alpine \
  | gzip > "$DIST_DIR/redis-7-alpine.tar.gz"

COMPOSE_FILE="$DIST_DIR/docker-compose.yml"
GENERATED_ADMIN_PASSWORD=""

if [ -f "$COMPOSE_FILE" ]; then
  say "配置" "已存在 ${COMPOSE_FILE}，保留原密码与配置，不覆盖"
else
  DB_PASSWORD="$(openssl rand -hex 24)"
  JWT_SECRET="$(openssl rand -hex 32)"
  GENERATED_ADMIN_PASSWORD="$(openssl rand -hex 12)"

  say "配置" "生成 ${COMPOSE_FILE}"
  cat > "$COMPOSE_FILE" <<EOF
# 极空间部署配置（Z4Pro+ 等 x86 NAS，镜像架构 linux/amd64）
# 使用方法：
#   1. Docker → 镜像 → 导入，依次导入 startools-backend.tar.gz、startools-frontend.tar.gz、
#      postgres-16-alpine.tar.gz、redis-7-alpine.tar.gz（每个包只含一个镜像）
#   2. Docker → Compose → 新建项目，项目名称填 startools
#   3. 存储位置选一个新建的空目录，把本文件放进去或直接粘贴到 Compose 编辑框
# 提示：修改数据库密码、管理台密码或 JWT 密钥后，需保证同一服务内相关字段同步修改。
# 若之前部署失败过，请更换项目名或删除旧项目的数据卷后再启动，避免旧数据库密码与当前配置冲突。
services:
  db:
    image: postgres:16-alpine
    environment:
      # 数据库用户名、库名；下方 backend 的 DATABASE_URL 必须与此处保持一致
      POSTGRES_USER: startools
      # 数据库密码；修改后必须同步修改 backend 的 DATABASE_URL
      POSTGRES_PASSWORD: "${DB_PASSWORD}"
      POSTGRES_DB: startools
    volumes:
      # 数据库数据持久化卷；删除该卷会丢失全部数据
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U startools -d startools"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      # Redis 持久化数据（登录限流、任务状态等）
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  backend:
    # 后端镜像；重新打包导入新版本后，重建本服务即可升级
    image: startools-backend:latest
    environment:
      # 运行环境标识，部署时保持 production
      APP_ENV: production
      # 数据库连接串：用户名/密码/库名必须与 db 服务一致，主机名固定为 db
      DATABASE_URL: "postgresql+asyncpg://startools:${DB_PASSWORD}@db:5432/startools"
      # Redis 连接串，主机名固定为 redis
      REDIS_URL: "redis://redis:6379/0"
      # 允许跨域的前端地址（逗号分隔）。同域部署（经 Nginx 反代）可保持默认；
      # 若前端单独部署在其它域名，请填前端实际地址。端口应与 frontend 的宿主机端口一致
      CORS_ORIGINS: "${NAS_URL}"
      # 管理台账号密码，建议部署前改成强密码
      ADMIN_USERNAME: "${ADMIN_USERNAME}"
      ADMIN_PASSWORD: "${GENERATED_ADMIN_PASSWORD}"
      # 管理台登录凭证签名密钥；修改后所有已登录会话失效，请妥善保存
      JWT_SECRET: "${JWT_SECRET}"
      # 通过 HTTPS 访问时改为 "true"，否则浏览器可能不保存管理台登录 Cookie
      COOKIE_SECURE: "${COOKIE_SECURE}"
      # 上传文件与处理结果的容器内目录，对应下方 backend_storage 卷
      STORAGE_DIR: "/app/storage"
      # 语音识别模型目录（已打包进镜像，一般无需修改）
      MODELS_DIR: "/app/models"
      # 模型下载源，国内网络保持镜像地址即可
      HF_ENDPOINT: "https://hf-mirror.com"
      # 磁盘使用率达到该百分比时停止接收新任务（80 表示 80%）
      DISK_STOP_PERCENT: "80"
    volumes:
      # 用户上传文件与处理结果持久化；删除该卷会丢失历史文件
      - backend_storage:/app/storage
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
      interval: 15s
      timeout: 5s
      # NAS 首次启动需要初始化数据库，等待时间适当放宽
      retries: 10
      start_period: 60s
    restart: unless-stopped

  frontend:
    # 前端镜像（Nginx + 静态资源 + /api 反向代理）
    image: startools-frontend:latest
    ports:
      # "宿主机端口:容器端口"；端口被占用时只改冒号左侧，例如 "9056:80"
      - "${NAS_PORT}:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  # 命名卷由 Docker 管理；除非确认不再需要数据，否则不要删除
  pgdata:
  redisdata:
  backend_storage:
EOF
  chmod 600 "$COMPOSE_FILE"
fi

say "完成" "产物位于 ${DIST_DIR}"
printf '  %s\n' \
  "$DIST_DIR/docker-compose.yml" \
  "$DIST_DIR/startools-backend.tar.gz" \
  "$DIST_DIR/startools-frontend.tar.gz" \
  "$DIST_DIR/postgres-16-alpine.tar.gz" \
  "$DIST_DIR/redis-7-alpine.tar.gz"

printf '\n极空间操作：\n'
printf '  1. Docker → 镜像 → 导入，依次导入 4 个镜像包（每个包只含一个镜像）\n'
printf '  2. Docker → Compose → 创建项目，项目名称填 startools\n'
printf '  3. 存储位置新建空目录，导入或粘贴 docker-compose.yml\n'
printf '  4. 访问 http://NAS的局域网IP:%s/startools/\n' "$NAS_PORT"
printf '  5. 管理台 http://NAS的局域网IP:%s/startools/admin/login\n' "$NAS_PORT"

if [ -n "$GENERATED_ADMIN_PASSWORD" ]; then
  printf '\n管理台账号：%s\n管理台密码：%s\n' "$ADMIN_USERNAME" "$GENERATED_ADMIN_PASSWORD"
  printf '数据库密码和 JWT 已写入 compose 文件，请妥善保存。\n'
else
  printf '\n已有配置未被覆盖，管理员密码请查看 %s\n' "$COMPOSE_FILE"
fi

if [ "$COOKIE_SECURE" = "true" ]; then
  printf '\n当前 NAS_URL 是 HTTPS，COOKIE_SECURE 已设为 true。\n'
else
  printf '\n当前是 HTTP 部署，COOKIE_SECURE=false；以后启用 HTTPS 时要改成 true。\n'
fi

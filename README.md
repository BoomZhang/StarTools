# 随手工具箱 StarTools

一个访客免登录、管理台可配置的日常工具站。网站名称、Logo 文字、处理位置徽章、隐私说明入口、上传确认与反馈入口都可在管理台切换；图片与文档默认在服务端处理，也可由管理台按工具切换为浏览器前端处理；文字、编码、二维码等轻量工具只在本机处理。

- 前端：Vue 3 + Vite + TypeScript + vue-router + axios
- 后端：FastAPI + SQLAlchemy 2（async）+ asyncpg
- 中间件：PostgreSQL 16、Redis 7
- 生产入口：Nginx（静态资源 + `/api` 反向代理）
- 部署：Docker Compose，站点统一挂在 `/startools` 子路径

---

## 一、快速开始

### 1. 本机开发（前后端分开运行）

```bash
# 首次执行：生成 env 文件、安装前后端依赖、准备语音模型
./scripts/setup.sh

# 一键启动开发环境：db + redis 容器、FastAPI 8000、Vite 5173
./scripts/dev.sh
```

启动后：

| 服务 | 地址 |
| --- | --- |
| 前端开发站点 | http://127.0.0.1:5173/startools/ |
| 开发环境管理台 | http://127.0.0.1:5173/startools/admin/login |
| 后端 API | http://127.0.0.1:8000 |
| 接口文档 | http://127.0.0.1:8000/api/docs |
| 健康检查 | http://127.0.0.1:8000/api/health |

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`，访问 `/` 会自动跳转到 `/startools/`。

默认 39 个工具全部上线，可在管理台逐工具关闭。默认管理台账号为 `admin` / `startools-admin`，仅用于本机开发。

### 2. 分开调试

开两个终端：

```bash
# 终端 1：db + redis + 后端
./scripts/dev-backend.sh

# 终端 2：前端 Vite
./scripts/dev-frontend.sh
```

### 3. Docker Compose 一键运行

```bash
./scripts/up.sh
```

启动后：

| 服务 | 地址 |
| --- | --- |
| 访客站点 | http://127.0.0.1:8080/startools/ |
| 管理台登录 | http://127.0.0.1:8080/startools/admin/login |
| 接口文档 | http://127.0.0.1:8080/api/docs |
| 健康检查 | http://127.0.0.1:8080/api/health |

默认管理台账号：`admin` / `startools-admin`。**正式部署前必须修改 `.env` 中的 `ADMIN_PASSWORD` 与 `JWT_SECRET`。**

```bash
./scripts/down.sh              # 停止服务，保留数据卷
./scripts/down.sh --volumes    # 停止并删除数据库、Redis、原始文件数据（不可恢复）
```

---

## 二、脚本说明

| 脚本 | 作用 |
| --- | --- |
| `scripts/setup.sh` | 复制 `.env` 示例、创建 Python venv、安装后端/前端依赖、缺失时下载 Whisper 模型 |
| `scripts/dev.sh` | 启动 db + redis，等待 PostgreSQL 就绪，同时启动后端与前端 |
| `scripts/dev-backend.sh` | 单独启动 db + redis + FastAPI（8000） |
| `scripts/dev-frontend.sh` | 单独启动 Vite（5173） |
| `scripts/test.sh` | 启动测试依赖，运行 pytest，再做前端类型检查与生产构建 |
| `scripts/up.sh` | 检查模型，`docker compose up -d --build`，打印访问地址 |
| `scripts/down.sh` | `docker compose down`，可加 `--volumes` 清空数据 |
| `scripts/fetch-models.sh` | 下载 Whisper base 语音识别模型（约 145MB，国内使用 hf-mirror） |

### 常用手工命令

```bash
# 查看容器与健康状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 只看最近 100 行
docker compose logs --tail=100 backend frontend

# 进入数据库
docker compose exec db psql -U startools -d startools

# 进入 Redis
docker compose exec redis redis-cli

# 单独重建后端
docker compose build backend && docker compose up -d backend

# 单独重建前端
docker compose build frontend && docker compose up -d frontend
```

---

## 三、页面与功能

### 访客页面

| 路由 | 页面 | 主要功能 |
| --- | --- | --- |
| `/startools/` | 首页 | 分类筛选与工具卡片；网站品牌、引擎徽章与隐私入口来自管理台配置 |
| `/startools/t/{slug}` | 工具页 | 输入、参数、唯一主按钮、处理状态、结果下载/复制、规则说明；返回首页时保留上次滚动位置 |
| `/startools/privacy` | 处理与隐私 | 前端/服务端边界、记录字段、30 天/1 小时/90 天保留规则、第三方能力披露 |
| `/startools/feedback` | 问题反馈 | 类型（含「希望增加其他工具」）、关联工具、描述、期望结果、联系方式、自动上下文；提交后显示 `FB-YYYYMMDD-####` |
| `/startools/*` | 404 | 说明页面不存在，保留搜索与 4 个热门工具 |
| `/` | 重定向 | 跳转到 `/startools/` |

工具页支持：

- 拖拽、点击选择、粘贴图片（二维码识别额外支持摄像头）
- 文件排序、移除、大小/数量/类型校验
- 管理台可关闭上传前确认；开启时服务端工具会提示文件会发送到服务器处理
- 上传进度、处理中、成功/部分成功/失败、错误编号与建议
- 结果下载、批量 ZIP、复制文本、删除结果
- 失败保留输入与参数，可重试；服务端任务可在 60 分钟内通过会话恢复
- 不记录最近使用；页脚「清除本机数据」只重置本机上传确认状态

图片、音频、视频格式覆盖：

- 图片输入：JPG、PNG、WebP、AVIF、HEIC、TIFF、BMP、GIF（首帧）、SVG
- 图片输出：JPG、PNG、WebP、AVIF、GIF（静态）、BMP、TIFF
- 音频：MP3、WAV、M4A、AAC、FLAC、OGG、OPUS、WMA、AIFF
- 视频：MP4、WebM、MOV、MKV、AVI、FLV、M4V、WMV、TS
- IMG-03 支持在图片上直接拖动裁剪框、四角缩放与常用比例；IMG-05 支持拖拽缩略图排序并预览拼接布局
- TXT-01 支持上传 TXT、Markdown、CSV、JSON、LOG、SRT、XML、YAML 等文本文件，在浏览器本地统计
- AV-03 除三档预设外，高级选项可设置 H.264/H.265、CRF/平均码率、preset、分辨率、帧率、音频编码、声道、采样率与裁剪起止时间

### 工具清单（39 项）

**图片（7）**：图片格式转换、图片压缩、尺寸调整与裁剪、图片加水印、图片拼接、图片取色、图标生成

**文档与 PDF（9）**：图片转 PDF、PDF 合并、PDF 拆分、PDF 转图片、PDF 页面管理、PDF 压缩、Office 转 PDF、PDF 转 Word、PDF 密码

**文字（4）**：文本统计、JSON 格式化、Markdown 预览、正则测试

**编码与生成（5）**：Base64 编解码、URL 编解码、哈希计算、时间戳转换、随机与密码

**二维码（4）**：二维码生成、二维码识别、批量二维码、二维码美化

**OCR（3）**：图片文字识别、PDF 文字识别、表格识别

**音视频与语音（7）**：音频格式转换、视频转 GIF、视频压缩、提取音频、视频格式转换、语音转文字、文字转语音

各工具 slug 可在首页卡片或 `/api/site` 的 `tools[].slug` 中查看，例如：

- `/startools/t/image-convert` 图片格式转换
- `/startools/t/pdf-merge` PDF 合并
- `/startools/t/markdown-preview` Markdown 预览
- `/startools/t/qr-generate` 二维码生成
- `/startools/t/speech-to-text` 语音转文字

### 管理台

| 路由 | 页面 | 主要功能 |
| --- | --- | --- |
| `/startools/admin/login` | 登录 | 单账号登录；连续失败 5 次锁定 10 分钟；会话 8 小时 |
| `/startools/admin` | 概览 | 今日/区间使用量、服务端占比、磁盘、待处理反馈、趋势、排行、引擎占比、工具明细 |
| `/startools/admin/settings` | 站点设置 | 网站名称、Logo 文字、处理位置徽章、隐私说明入口、上传前确认、问题反馈入口 |
| `/startools/admin/tools` | 工具配置 | 39 项逐工具上线开关、服务端开关、单文件上限、单次数量；高风险操作二次确认 |
| `/startools/admin/usage` | 使用记录 | 时间、工具、结果、引擎、耗时、文件数、大小、IP、错误编号；按工具/结果/引擎/IP/天数筛选 |
| `/startools/admin/feedback` | 问题反馈 | 状态筛选、详情、状态流转、内部备注；反馈入口可在站点设置统一开关 |
| `/startools/admin/raw` | 原始数据 | 服务端原始文件列表、预览、下载、提前删除、手动清理到期数据 |
| `/startools/admin/audit` | 操作记录 | 登录、配置变更、反馈处理、原始数据访问/删除、手动清理 |

管理台页面均带 `noindex, nofollow`，不进入公开导航，也不被搜索引擎索引。

站点名称、Logo 文字与各展示模块直接保存在数据库，可在「站点设置」修改；保存后访客页面最多 10 秒同步，无需重启服务。

---

## 四、配置项

根目录 `.env` 用于 Docker Compose；`backend/.env` 用于本机后端开发。两者都从对应 `.env.example` 复制。

| 变量 | 说明 |
| --- | --- |
| `APP_PORT` | Compose 对外端口，默认 `8080` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 管理台单账号；部署前必须修改 |
| `JWT_SECRET` | 管理台会话签名密钥；部署前必须改为随机长字符串 |
| `COOKIE_SECURE` | HTTPS 部署时设为 `true` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 数据库配置 |
| `DATABASE_URL` | 本机后端连接串；容器内由 Compose 注入 |
| `REDIS_URL` | Redis 连接串 |
| `CORS_ORIGINS` | 允许跨域的前端来源，逗号分隔 |
| `STORAGE_DIR` | 服务端原始文件与结果目录，容器内为 `/app/storage` |
| `MODELS_DIR` | 语音模型目录，容器内为 `/app/models` |
| `WHISPER_MODEL_SIZE` | Whisper 模型规格，默认 `base` |
| `HF_ENDPOINT` | 模型下载镜像，默认 `https://hf-mirror.com` |
| `DISK_STOP_PERCENT` | 磁盘保护阈值；PRD 正式值为 80，本机示例为 95 |
| `APT_MIRROR` / `PIP_INDEX_URL` | 国内构建镜像源，可按网络环境调整 |

### 数据保留

- 服务端原始文件：30 天
- 服务端结果：1 小时
- 使用记录、反馈、管理操作记录：90 天
- 每日自动清理一次，服务启动时补清理一次；登录后可在「原始数据」页手动清理

### 限流与安全

- 服务端任务：每 IP 30 次/小时
- 问题反馈：每 IP 5 条/小时；同 IP、同工具、相同描述 10 分钟内拒绝重复提交
- 管理台登录：同账号加 IP 10 分钟内失败 5 次锁定 10 分钟
- PDF 密码与文字转语音文本不会写入任务参数、日志、使用记录或操作记录
- 单实例部署；原始文件保存在本地持久磁盘，不使用对象存储

---

## 五、发布流程

### 1. 发布前检查

```bash
# 修改生产配置
cp .env.example .env
# 编辑 .env：
#   ADMIN_PASSWORD / JWT_SECRET 必须替换
#   DISK_STOP_PERCENT 建议改回 80
#   HTTPS 部署时 COOKIE_SECURE=true
#   CORS_ORIGINS 改为实际访问域名

# 准备语音模型（缺失时 up.sh 也会自动下载）
./scripts/fetch-models.sh

# 本地校验
./scripts/test.sh
```

### 2. 构建并启动

```bash
./scripts/up.sh
# 等价于
docker compose up -d --build
```

首次构建会拉取/构建 Python、Node、Nginx 基础镜像，并安装 LibreOffice、ffmpeg、Tesseract 等引擎；后端镜像较大，构建时间取决于网络。

### 3. 发布后验证

```bash
curl -s http://127.0.0.1:8080/api/health
curl -s http://127.0.0.1:8080/api/site
docker compose ps
```

确认：

- `backend`、`db`、`redis` 为 healthy，`frontend` 为 Up
- `/startools/`、`/startools/admin/login`、`/api/docs` 返回 200
- 管理台可登录；工具配置页显示 39 项
- 上传一个小图片执行图片格式转换，结果可下载

### 4. 升级与回滚

```bash
# 升级：重新构建并滚动重启
./scripts/up.sh

# 仅重启某个服务
docker compose restart backend

# 回滚代码后重新构建
docker compose build backend frontend && docker compose up -d
```

数据卷：`startools_pgdata`、`startools_redisdata`、`startools_backend_storage`。`down --volumes` 会删除这些卷，属于不可恢复操作。

---

## 六、目录结构

```text
StarTools/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI 入口与生命周期
│   │   ├── catalog.py           39 个工具元数据
│   │   ├── api/routes/           公共、任务、管理台接口
│   │   ├── core/                 配置、数据库/Redis 连接、会话安全
│   │   ├── db/                   ORM 模型与种子数据
│   │   └── services/             图片、PDF、OCR、音视频处理与清理
│   ├── models/                   Whisper 本地模型（gitignore）
│   ├── tests/                    pytest
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/                首页、工具页、隐私、反馈、管理台
│   │   ├── components/tools/     39 个工具页面组件
│   │   ├── api/                  axios 接口封装
│   │   ├── composables/          站点配置、上传确认、任务状态
│   │   └── styles/               纸张工作台设计系统
│   ├── nginx.conf
│   └── Dockerfile
├── scripts/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 七、常见问题

**管理台登录被锁定**
同一账号加 IP 10 分钟内失败 5 次会锁定 10 分钟。等待后重试，或清理 Redis 中的 `startools:login:*` 键。

**服务端任务提示「本小时服务端任务已达上限」**
每 IP 每小时 30 次。等待恢复，或使用前端工具。开发调试可删除 Redis 中的 `startools:task:{IP}` 键。

**DOC-07 Office 转 PDF 显示不可用**
本机开发需要安装 LibreOffice：`brew install --cask libreoffice`。Docker 镜像已内置，无需额外安装。

**AV-06 语音转文字首次很慢或失败**
确认 `backend/models/whisper/base/model.bin` 存在；缺失时执行 `./scripts/fetch-models.sh`。Docker 镜像构建时已复制本地模型。

**Docker 拉取基础镜像超时**
国内网络可配置 Docker Hub 镜像加速，或在 `.env` 中调整 `APT_MIRROR`、`PIP_INDEX_URL`；语音模型使用 `HF_ENDPOINT` 镜像。

**磁盘保护导致服务端任务不可用**
`DISK_STOP_PERCENT` 达到阈值后服务端任务会停止接收，前端工具仍可用。本机开发默认示例为 95，正式部署建议改回 80。

**修改管理台密码后不生效**
密码与会话密钥在应用启动时读取，修改 `.env` 后需重启后端：
`docker compose up -d backend`。

---

## 八、已知边界

- 双端工具默认使用服务端。图片 P1 的 IMG-04/05/07 与文档 DOC-01~05 暂无浏览器前端实现；管理台切到前端时会明确提示切回服务端，不会静默切换。
- 服务端任务为同步处理，当前没有排队队列与取消界面；OCR、音视频等长任务会持续显示处理中。
- 纯前端工具的结果只存在当前页面内存，刷新即丢失；服务端结果仍在后台按保留策略清理，但工具页不展示保存倒计时。
- 语音识别准确率取决于 Whisper base 模型与音频质量，结果需人工校对。
- 站点为单实例设计，不面向多租户集群；原始文件与结果保存在本地磁盘。

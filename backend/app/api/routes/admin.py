"""管理台：登录、概览、工具配置、使用记录、反馈、原始数据与操作记录。"""

import shutil
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import CATEGORY_MAP, CODE_MAP, TOOLS
from app.core.clients import get_db
from app.core.config import settings
from app.core.security import create_token, require_admin, verify_credentials
from app.db.models import (
    AuditRecord,
    Feedback,
    FeedbackEvent,
    RawFile,
    SiteSetting,
    ToolConfig,
    UsageRecord,
)
from app.domain import (
    ALLOWED_FEEDBACK_TRANSITIONS,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    SINGLE_FILE_CODES,
    hard_file_limit_mb,
    max_count_limit,
)
from app.services.common import client_ip
from app.services.config_service import load_configs, setting_bool, site_setting
from app.services.limits import (
    clear_login_failures,
    lock_login,
    record_login_failure,
    write_audit,
)
from app.services.runner import availability

admin_auth = APIRouter(prefix="/admin", tags=["admin"])
admin = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)], tags=["admin"])


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


@admin_auth.post("/login", summary="维护者登录")
async def admin_login(
    payload: LoginPayload,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict:
    ip = client_ip(request)
    redis = request.app.state.redis
    locked, retry_at = await lock_login(
        redis, ip, payload.username, settings.login_max_failures, settings.login_lock_minutes
    )
    if locked:
        retry_label = retry_at.astimezone().strftime("%H:%M") if retry_at else "稍后"
        raise HTTPException(
            status_code=429,
            detail={"message": f"登录失败次数过多，请在 {retry_label} 后重试", "retry_at": retry_at.isoformat() if retry_at else None},
        )

    if not verify_credentials(payload.username, payload.password):
        await record_login_failure(
            redis, ip, payload.username, settings.login_max_failures, settings.login_lock_minutes
        )
        write_audit(session, payload.username, "login_failed", "admin", {"username": payload.username}, ip)
        await session.commit()
        raise HTTPException(status_code=401, detail={"message": "账号或密码错误"})

    await clear_login_failures(redis, ip, payload.username)
    write_audit(session, payload.username, "login", "admin", {}, ip)
    await session.commit()

    token = create_token()
    response.set_cookie(
        settings.admin_cookie_name,
        token,
        max_age=settings.admin_session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return {"username": settings.admin_username, "expires_in": settings.admin_session_hours * 3600}


@admin_auth.post("/logout", summary="退出登录")
async def admin_logout(response: Response) -> dict:
    response.delete_cookie(settings.admin_cookie_name, path="/")
    return {"ok": True}


@admin.get("/me", summary="当前登录账号")
async def admin_me(username: str = Depends(require_admin)) -> dict:
    return {"username": username}


def _days_range(days: int) -> tuple[datetime, datetime, datetime]:
    tz = ZoneInfo(settings.site_timezone)
    now_local = datetime.now(tz)
    today_start = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    start_local = today_start - timedelta(days=days - 1)
    return start_local.astimezone(UTC), now_local, tz


@admin.get("/overview", summary="管理台概览")
async def overview(days: int = 30, session: AsyncSession = Depends(get_db)) -> dict:
    if days not in {7, 30, 90}:
        days = 30
    start, now_local, tz = _days_range(days)
    today_start = datetime.combine(now_local.date(), time.min, tzinfo=tz).astimezone(UTC)

    total = await session.scalar(select(func.count()).select_from(UsageRecord).where(UsageRecord.created_at >= start)) or 0
    today = await session.scalar(
        select(func.count()).select_from(UsageRecord).where(UsageRecord.created_at >= today_start)
    ) or 0
    server_tasks = await session.scalar(
        select(func.count())
        .select_from(UsageRecord)
        .where(UsageRecord.created_at >= start, UsageRecord.engine == "server")
    ) or 0
    online_tools = await session.scalar(
        select(func.count()).select_from(ToolConfig).where(ToolConfig.online.is_(True))
    ) or 0
    raw_bytes = int(
        await session.scalar(select(func.coalesce(func.sum(RawFile.size), 0))) or 0
    )
    pending_feedback = await session.scalar(
        select(func.count()).select_from(Feedback).where(Feedback.status == "pending")
    ) or 0

    day_expr = func.to_char(func.timezone(settings.site_timezone, UsageRecord.created_at), "YYYY-MM-DD")
    daily_rows = (
        await session.execute(
            select(day_expr.label("day"), func.count().label("count"))
            .where(UsageRecord.created_at >= start)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()
    daily_map = {row.day: row.count for row in daily_rows}
    daily = []
    for offset in range(days):
        day = (now_local.date() - timedelta(days=days - 1 - offset)).isoformat()
        daily.append({"date": day, "count": daily_map.get(day, 0)})

    ranking_rows = (
        await session.execute(
            select(UsageRecord.tool_code, UsageRecord.tool_name, func.count().label("count"))
            .where(UsageRecord.created_at >= start)
            .group_by(UsageRecord.tool_code, UsageRecord.tool_name)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    ranking = [
        {
            "code": row.tool_code,
            "name": row.tool_name,
            "count": row.count,
            "ratio": round(row.count / total * 100, 1) if total else 0,
        }
        for row in ranking_rows
    ]

    engine_rows = (
        await session.execute(
            select(UsageRecord.engine, func.count().label("count"))
            .where(UsageRecord.created_at >= start)
            .group_by(UsageRecord.engine)
        )
    ).all()
    engine_split = {"server": 0, "local": 0}
    for row in engine_rows:
        engine_split[row.engine] = row.count

    stat_rows = (
        await session.execute(
            select(
                UsageRecord.tool_code,
                UsageRecord.tool_name,
                func.count().label("total"),
                func.sum(case((UsageRecord.result == "succeeded", 1), else_=0)).label("succeeded"),
                func.sum(case((UsageRecord.result == "partial", 1), else_=0)).label("partial"),
                func.sum(case((UsageRecord.result == "failed", 1), else_=0)).label("failed"),
                func.sum(case((UsageRecord.result == "canceled", 1), else_=0)).label("canceled"),
                func.max(UsageRecord.created_at).label("last_used"),
            )
            .where(UsageRecord.created_at >= start)
            .group_by(UsageRecord.tool_code, UsageRecord.tool_name)
        )
    ).all()
    stats_map = {row.tool_code: row for row in stat_rows}

    latest_rows = (
        await session.execute(
            select(UsageRecord.tool_code, UsageRecord.ip, UsageRecord.created_at)
            .where(UsageRecord.created_at >= start)
            .distinct(UsageRecord.tool_code)
            .order_by(UsageRecord.tool_code, UsageRecord.created_at.desc())
        )
    ).all()
    latest_ip = {row.tool_code: row.ip for row in latest_rows}

    tool_table = []
    for tool in TOOLS:
        row = stats_map.get(tool.code)
        last_used = row.last_used.isoformat() if row and row.last_used else None
        tool_table.append(
            {
                "code": tool.code,
                "name": tool.name,
                "category": CATEGORY_MAP[tool.category].name,
                "priority": tool.priority,
                "implemented": tool.implemented,
                "total": row.total if row else 0,
                "succeeded": row.succeeded if row else 0,
                "partial": row.partial if row else 0,
                "failed": row.failed if row else 0,
                "canceled": row.canceled if row else 0,
                "last_used": last_used,
                "last_ip": latest_ip.get(tool.code),
            }
        )

    feedback_rows = (
        await session.execute(select(Feedback.status, func.count()).group_by(Feedback.status))
    ).all()
    feedback_counts = {status: 0 for status in FEEDBACK_STATUSES}
    for status, count in feedback_rows:
        feedback_counts[status] = count

    disk = shutil.disk_usage(settings.storage_path)

    return {
        "days": days,
        "metrics": {
            "today": today,
            "total": total,
            "online_tools": online_tools,
            "total_tools": len(TOOLS),
            "server_tasks": server_tasks,
            "server_ratio": round(server_tasks / total * 100, 1) if total else 0,
            "raw_bytes": raw_bytes,
            "disk": {
                "percent": round(disk.used / disk.total * 100, 1),
                "free": disk.free,
                "total": disk.total,
            },
            "pending_feedback": pending_feedback,
        },
        "daily": daily,
        "ranking": ranking,
        "engine_split": engine_split,
        "tool_table": tool_table,
        "feedback_counts": feedback_counts,
    }


def _admin_tool_payload(tool, config: ToolConfig) -> dict:
    available, reason = availability(tool)
    if not tool.implemented:
        status = "unimplemented"
    elif not config.online:
        status = "offline"
    else:
        status = "live"
    return {
        "code": tool.code,
        "name": tool.name,
        "slug": tool.slug,
        "category": tool.category,
        "category_name": CATEGORY_MAP[tool.category].name,
        "priority": tool.priority,
        "engine_type": tool.engine,
        "summary": tool.summary,
        "implemented": tool.implemented,
        "accepts_files": tool.accepts_files,
        "online": config.online,
        "server_enabled": config.server_enabled,
        "max_file_mb": config.max_file_mb,
        "max_count": config.max_count,
        "hard_limit_mb": hard_file_limit_mb(tool),
        "fixed_count": tool.code in SINGLE_FILE_CODES,
        "available": available,
        "unavailable_reason": reason,
        "status": status,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        "updated_by": config.updated_by,
    }


@admin.get("/tools", summary="全部工具配置")
async def list_admin_tools(session: AsyncSession = Depends(get_db)) -> dict:
    configs = await load_configs(session)
    groups = []
    for category in CATEGORY_MAP.values():
        items = [
            _admin_tool_payload(tool, configs[tool.code])
            for tool in TOOLS
            if tool.category == category.key and configs.get(tool.code)
        ]
        groups.append(
            {
                "key": category.key,
                "name": category.name,
                "blurb": category.blurb,
                "tools": items,
            }
        )
    return {"groups": groups}


class ToolConfigPatch(BaseModel):
    online: bool | None = None
    server_enabled: bool | None = None
    max_file_mb: int | None = None
    max_count: int | None = None


@admin.patch("/tools/{code}", summary="修改工具配置")
async def update_tool(
    code: str,
    payload: ToolConfigPatch,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    tool = CODE_MAP.get(code)
    if tool is None:
        raise HTTPException(status_code=404, detail="工具不存在")
    config = await session.scalar(select(ToolConfig).where(ToolConfig.code == code))
    if config is None:
        raise HTTPException(status_code=404, detail="工具配置不存在")

    before = {
        "online": config.online,
        "server_enabled": config.server_enabled,
        "max_file_mb": config.max_file_mb,
        "max_count": config.max_count,
    }
    changes: dict = {}

    if payload.online is not None:
        if payload.online and not tool.implemented:
            raise HTTPException(status_code=400, detail="P1 工具未实现前不可上线")
        config.online = payload.online
        changes["online"] = payload.online

    if payload.server_enabled is not None:
        if tool.engine == "server" and not payload.server_enabled:
            raise HTTPException(status_code=400, detail="该工具无前端实现，服务端处理不可关闭")
        if tool.engine == "local" and payload.server_enabled:
            raise HTTPException(status_code=400, detail="该工具无服务端实现，服务端处理不可开启")
        config.server_enabled = payload.server_enabled
        changes["server_enabled"] = payload.server_enabled

    if payload.max_file_mb is not None:
        if not tool.accepts_files:
            raise HTTPException(status_code=400, detail="该工具不接受文件输入，无需设置单文件上限")
        hard = hard_file_limit_mb(tool)
        if not 1 <= payload.max_file_mb <= hard:
            raise HTTPException(status_code=400, detail=f"单文件上限需在 1–{hard}MB 之间")
        config.max_file_mb = payload.max_file_mb
        changes["max_file_mb"] = payload.max_file_mb

    if payload.max_count is not None:
        limit = max_count_limit(tool)
        if payload.max_count < 1 or payload.max_count > limit:
            raise HTTPException(
                status_code=400,
                detail="该工具仅接受单文件，数量固定为 1" if limit == 1 else f"单次数量需在 1–{limit} 之间",
            )
        config.max_count = payload.max_count
        changes["max_count"] = payload.max_count

    if not changes:
        raise HTTPException(status_code=400, detail="没有需要保存的变更")

    config.updated_by = actor
    config.updated_at = datetime.now(UTC)
    write_audit(
        session,
        actor,
        "tool.update",
        code,
        {"before": before, "after": changes},
        client_ip(request),
    )
    await session.commit()
    await session.refresh(config)
    return {"tool": _admin_tool_payload(tool, config)}


class FeedbackStatusPayload(BaseModel):
    status: str


class FeedbackNotePayload(BaseModel):
    content: str = Field(min_length=1, max_length=1000)


class FeedbackTogglePayload(BaseModel):
    enabled: bool


class SiteSettingsPayload(BaseModel):
    site_name: str | None = Field(default=None, min_length=1, max_length=30)
    logo_text: str | None = Field(default=None, min_length=1, max_length=2)
    feedback_enabled: bool | None = None
    privacy_links_enabled: bool | None = None
    upload_consent_enabled: bool | None = None
    show_engine_badge: bool | None = None


def _settings_payload(values: dict[str, str]) -> dict:
    return {
        "site_name": site_setting(values, "site_name"),
        "logo_text": site_setting(values, "logo_text"),
        "feedback_enabled": setting_bool(values, "feedback_enabled"),
        "privacy_links_enabled": setting_bool(values, "privacy_links_enabled"),
        "upload_consent_enabled": setting_bool(values, "upload_consent_enabled"),
        "show_engine_badge": setting_bool(values, "show_engine_badge"),
    }


@admin.get("/feedback", summary="反馈列表")
async def list_feedback(
    status: str | None = None,
    type: str | None = None,
    tool: str | None = None,
    days: int = 30,
    q: str | None = None,
    page: int = 1,
    session: AsyncSession = Depends(get_db),
) -> dict:
    if days not in {7, 30, 90}:
        days = 30
    start, _, _ = _days_range(days)
    page = max(1, page)

    conditions = [Feedback.created_at >= start]
    if status and status in FEEDBACK_STATUSES:
        conditions.append(Feedback.status == status)
    if type and type in FEEDBACK_TYPES:
        conditions.append(Feedback.type == type)
    if tool:
        conditions.append(Feedback.tool_code == tool)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(or_(Feedback.description.ilike(pattern), Feedback.expected.ilike(pattern)))

    total = await session.scalar(select(func.count()).select_from(Feedback).where(*conditions)) or 0
    rows = (
        await session.scalars(
            select(Feedback)
            .where(*conditions)
            .order_by(Feedback.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ).all()

    counts_rows = (
        await session.execute(
            select(Feedback.status, func.count()).where(Feedback.created_at >= start).group_by(Feedback.status)
        )
    ).all()
    counts = {key: 0 for key in FEEDBACK_STATUSES}
    for key, value in counts_rows:
        counts[key] = value

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + 49) // 50),
        "counts": counts,
        "items": [
            {
                "id": row.id,
                "number": row.number,
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
                "type": row.type,
                "type_name": FEEDBACK_TYPES.get(row.type, row.type),
                "tool_code": row.tool_code,
                "tool_name": CODE_MAP[row.tool_code].name if row.tool_code in CODE_MAP else None,
                "description": row.description[:40],
                "status": row.status,
                "status_name": FEEDBACK_STATUSES.get(row.status, row.status),
                "ip": row.ip,
            }
            for row in rows
        ],
    }


async def _feedback_detail(session: AsyncSession, feedback_id: int) -> dict:
    row = await session.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    events = (
        await session.scalars(
            select(FeedbackEvent).where(FeedbackEvent.feedback_id == feedback_id).order_by(FeedbackEvent.created_at)
        )
    ).all()
    return {
        "id": row.id,
        "number": row.number,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "type": row.type,
        "type_name": FEEDBACK_TYPES.get(row.type, row.type),
        "tool_code": row.tool_code,
        "tool_name": CODE_MAP[row.tool_code].name if row.tool_code in CODE_MAP else None,
        "description": row.description,
        "expected": row.expected,
        "contact": row.contact,
        "context": row.context,
        "ip": row.ip,
        "status": row.status,
        "status_name": FEEDBACK_STATUSES.get(row.status, row.status),
        "events": [
            {
                "id": event.id,
                "kind": event.kind,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "note": event.note,
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }


@admin.get("/feedback/{feedback_id}", summary="反馈详情")
async def feedback_detail(feedback_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    return await _feedback_detail(session, feedback_id)


@admin.patch("/feedback/{feedback_id}/status", summary="变更反馈状态")
async def update_feedback_status(
    feedback_id: int,
    payload: FeedbackStatusPayload,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    row = await session.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    if payload.status not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=400, detail="未知状态")
    if payload.status not in ALLOWED_FEEDBACK_TRANSITIONS.get(row.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"不能从「{FEEDBACK_STATUSES.get(row.status)}」直接变更为「{FEEDBACK_STATUSES.get(payload.status)}」",
        )

    previous = row.status
    row.status = payload.status
    row.updated_at = datetime.now(UTC)
    session.add(
        FeedbackEvent(
            feedback_id=row.id,
            kind="status",
            from_status=previous,
            to_status=payload.status,
            actor=actor,
        )
    )
    write_audit(
        session,
        actor,
        "feedback.status",
        row.number,
        {"from": previous, "to": payload.status},
        client_ip(request),
    )
    await session.commit()
    return await _feedback_detail(session, feedback_id)


@admin.post("/feedback/{feedback_id}/notes", summary="添加内部备注")
async def add_feedback_note(
    feedback_id: int,
    payload: FeedbackNotePayload,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    row = await session.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="反馈不存在")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="备注不能为空")
    row.updated_at = datetime.now(UTC)
    session.add(
        FeedbackEvent(
            feedback_id=row.id,
            kind="note",
            note=content,
            actor=actor,
        )
    )
    write_audit(session, actor, "feedback.note", row.number, {"length": len(content)}, client_ip(request))
    await session.commit()
    return await _feedback_detail(session, feedback_id)


@admin.get("/settings", summary="管理台站点设置")
async def get_admin_settings(session: AsyncSession = Depends(get_db)) -> dict:
    rows = (await session.scalars(select(SiteSetting))).all()
    return _settings_payload({row.key: row.value for row in rows})


@admin.patch("/settings", summary="更新站点设置")
async def update_admin_settings(
    payload: SiteSettingsPayload,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    rows = {row.key: row for row in (await session.scalars(select(SiteSetting))).all()}
    before = _settings_payload({key: row.value for key, row in rows.items()})
    changes: dict = {}

    if payload.site_name is not None:
        name = payload.site_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="站点名称不能为空")
        changes["site_name"] = name
    if payload.logo_text is not None:
        logo = payload.logo_text.strip()
        if not logo:
            raise HTTPException(status_code=400, detail="Logo 文字不能为空")
        changes["logo_text"] = logo[:2]

    for key in (
        "feedback_enabled",
        "privacy_links_enabled",
        "upload_consent_enabled",
        "show_engine_badge",
    ):
        value = getattr(payload, key)
        if value is not None:
            changes[key] = value

    if not changes:
        raise HTTPException(status_code=400, detail="没有需要保存的变更")

    for key, value in changes.items():
        row = rows.get(key)
        stored = ("true" if value else "false") if isinstance(value, bool) else str(value)
        if row is None:
            session.add(SiteSetting(key=key, value=stored))
        else:
            row.value = stored

    after = changes
    write_audit(session, actor, "settings.update", "site", {"before": before, "after": after}, client_ip(request))
    await session.commit()

    refreshed = {row.key: row.value for row in (await session.scalars(select(SiteSetting))).all()}
    return _settings_payload(refreshed)


@admin.patch("/settings/feedback", summary="切换反馈入口")
async def toggle_feedback(
    payload: FeedbackTogglePayload,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    row = await session.get(SiteSetting, "feedback_enabled")
    if row is None:
        row = SiteSetting(key="feedback_enabled", value="true")
        session.add(row)
    previous = row.value == "true"
    row.value = "true" if payload.enabled else "false"
    write_audit(
        session,
        actor,
        "settings.feedback",
        "feedback",
        {"from": previous, "to": payload.enabled},
        client_ip(request),
    )
    await session.commit()
    return {"feedback_enabled": payload.enabled}


@admin.get("/usage", summary="使用记录")
async def list_usage(
    days: int = 30,
    tool: str | None = None,
    result: str | None = None,
    engine: str | None = None,
    ip: str | None = None,
    page: int = 1,
    session: AsyncSession = Depends(get_db),
) -> dict:
    if days not in {7, 30, 90}:
        days = 30
    start, _, _ = _days_range(days)
    page = max(1, page)
    conditions = [UsageRecord.created_at >= start]
    if tool:
        conditions.append(UsageRecord.tool_code == tool)
    if result:
        conditions.append(UsageRecord.result == result)
    if engine in {"server", "local"}:
        conditions.append(UsageRecord.engine == engine)
    if ip:
        conditions.append(UsageRecord.ip == ip.strip())

    total = await session.scalar(select(func.count()).select_from(UsageRecord).where(*conditions)) or 0
    rows = (
        await session.scalars(
            select(UsageRecord)
            .where(*conditions)
            .order_by(UsageRecord.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + 49) // 50),
        "items": [
            {
                "id": row.id,
                "created_at": row.created_at.isoformat(),
                "tool_code": row.tool_code,
                "tool_name": row.tool_name,
                "result": row.result,
                "engine": row.engine,
                "duration_ms": row.duration_ms,
                "ip": row.ip,
                "file_count": row.file_count,
                "total_size": row.total_size,
                "error_code": row.error_code,
                "is_retry": row.is_retry,
            }
            for row in rows
        ],
    }


@admin.get("/raw", summary="服务端原始文件")
async def list_raw_files(
    days: int = 30,
    tool: str | None = None,
    ip: str | None = None,
    page: int = 1,
    session: AsyncSession = Depends(get_db),
) -> dict:
    if days not in {7, 30, 90}:
        days = 30
    start, _, _ = _days_range(days)
    page = max(1, page)
    conditions = [RawFile.created_at >= start]
    if tool:
        conditions.append(RawFile.tool_code == tool)
    if ip:
        conditions.append(RawFile.ip == ip.strip())

    total = await session.scalar(select(func.count()).select_from(RawFile).where(*conditions)) or 0
    rows = (
        await session.scalars(
            select(RawFile)
            .where(*conditions)
            .order_by(RawFile.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ).all()
    total_bytes = await session.scalar(select(func.coalesce(func.sum(RawFile.size), 0))) or 0

    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + 49) // 50),
        "total_bytes": total_bytes,
        "items": [
            {
                "id": row.id,
                "task_id": row.task_id,
                "tool_code": row.tool_code,
                "tool_name": CODE_MAP[row.tool_code].name if row.tool_code in CODE_MAP else row.tool_code,
                "filename": row.filename,
                "content_type": row.content_type,
                "size": row.size,
                "ip": row.ip,
                "created_at": row.created_at.isoformat(),
                "expires_at": row.expires_at.isoformat(),
            }
            for row in rows
        ],
    }


async def _raw_row(session: AsyncSession, raw_id: str) -> RawFile:
    row = await session.get(RawFile, raw_id)
    if row is None:
        raise HTTPException(status_code=404, detail="原始文件不存在")
    if not Path(row.stored_path).exists():
        raise HTTPException(status_code=410, detail="原始文件已不可用")
    return row


@admin.get("/raw/{raw_id}/preview", summary="预览原始文件")
async def preview_raw(
    raw_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
):
    row = await _raw_row(session, raw_id)
    write_audit(session, actor, "raw.preview", row.id, {"filename": row.filename}, client_ip(request))
    await session.commit()
    return FileResponse(
        row.stored_path,
        media_type=row.content_type,
        headers={"Content-Disposition": f'inline; filename="{row.id}"', "Cache-Control": "no-store"},
    )


@admin.get("/raw/{raw_id}/download", summary="下载原始文件")
async def download_raw(
    raw_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
):
    row = await _raw_row(session, raw_id)
    write_audit(session, actor, "raw.download", row.id, {"filename": row.filename}, client_ip(request))
    await session.commit()
    return FileResponse(row.stored_path, filename=row.filename, media_type=row.content_type)


@admin.delete("/raw/{raw_id}", summary="提前删除原始文件")
async def delete_raw(
    raw_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    row = await _raw_row(session, raw_id)
    Path(row.stored_path).unlink(missing_ok=True)
    write_audit(
        session,
        actor,
        "raw.delete",
        row.id,
        {"filename": row.filename, "size": row.size, "tool": row.tool_code},
        client_ip(request),
    )
    await session.delete(row)
    await session.commit()
    return {"ok": True}


@admin.get("/audit", summary="管理操作记录")
async def list_audit(
    days: int = 30, page: int = 1, session: AsyncSession = Depends(get_db)
) -> dict:
    if days not in {7, 30, 90}:
        days = 30
    start, _, _ = _days_range(days)
    page = max(1, page)
    total = await session.scalar(
        select(func.count()).select_from(AuditRecord).where(AuditRecord.created_at >= start)
    ) or 0
    rows = (
        await session.scalars(
            select(AuditRecord)
            .where(AuditRecord.created_at >= start)
            .order_by(AuditRecord.created_at.desc())
            .offset((page - 1) * 50)
            .limit(50)
        )
    ).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, (total + 49) // 50),
        "items": [
            {
                "id": row.id,
                "created_at": row.created_at.isoformat(),
                "actor": row.actor,
                "action": row.action,
                "target": row.target,
                "detail": row.detail,
                "ip": row.ip,
            }
            for row in rows
        ],
    }


@admin.post("/cleanup", summary="手动清理到期数据")
async def manual_cleanup(
    request: Request,
    session: AsyncSession = Depends(get_db),
    actor: str = Depends(require_admin),
) -> dict:
    from app.services.cleanup import cleanup_expired

    counts = await cleanup_expired(request.app.state.db_session)
    write_audit(session, actor, "cleanup.manual", "storage", counts, client_ip(request))
    await session.commit()
    return {"counts": counts}

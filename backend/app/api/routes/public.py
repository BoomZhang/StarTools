"""访客侧公开接口：站点配置、工具目录、使用上报与问题反馈。"""

import re
from datetime import UTC, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import CATEGORY_MAP, CODE_MAP, SLUG_MAP
from app.core.clients import get_db
from app.core.config import settings
from app.db.models import Feedback, FeedbackEvent, UsageRecord
from app.domain import FEEDBACK_TYPES, USAGE_RESULTS
from app.services.common import client_ip
from app.services.config_service import (
    effective_engine,
    get_site_settings,
    load_configs,
    public_tool,
    site_payload,
)
from app.services.limits import duplicate_key, rate_limit, reserve_duplicate_key

router = APIRouter(tags=["public"])


@router.get("/site", summary="站点公开配置与已上线工具")
async def site_info(session: AsyncSession = Depends(get_db)) -> dict:
    return await site_payload(session)


@router.get("/tools/{slug}", summary="工具详情与相关推荐")
async def tool_detail(slug: str, session: AsyncSession = Depends(get_db)) -> dict:
    tool = SLUG_MAP.get(slug)
    if tool is None:
        raise HTTPException(status_code=404, detail="工具不存在")
    configs = await load_configs(session)
    config = configs.get(tool.code)
    if config is None or not tool.implemented:
        raise HTTPException(
            status_code=410,
            detail={
                "message": "该工具尚未上线",
                "reason": "unimplemented",
                "tool": {
                    "code": tool.code,
                    "name": tool.name,
                    "slug": tool.slug,
                    "category": tool.category,
                    "category_name": CATEGORY_MAP[tool.category].name,
                },
            },
        )
    if not config.online:
        raise HTTPException(
            status_code=410,
            detail={
                "message": "该工具已被维护者下线",
                "reason": "offline",
                "tool": {
                    "code": tool.code,
                    "name": tool.name,
                    "slug": tool.slug,
                    "category": tool.category,
                    "category_name": CATEGORY_MAP[tool.category].name,
                },
            },
        )

    payload = public_tool(tool, config)
    return {"tool": payload}


class UsagePayload(BaseModel):
    tool_code: str
    result: str
    duration_ms: int = Field(default=0, ge=0, le=3_600_000)
    file_count: int = Field(default=0, ge=0, le=50)
    total_size: int = Field(default=0, ge=0)
    error_code: str | None = Field(default=None, max_length=24)
    is_retry: bool = False

    @field_validator("result")
    @classmethod
    def check_result(cls, value: str) -> str:
        if value not in USAGE_RESULTS:
            raise ValueError("未知的任务结果")
        return value


@router.post("/usage", status_code=204, summary="前端任务使用上报（不含内容）")
async def report_usage(
    payload: UsagePayload,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> None:
    tool = CODE_MAP.get(payload.tool_code)
    if tool is None or not tool.implemented:
        raise HTTPException(status_code=400, detail="未知工具")
    configs = await load_configs(session)
    config = configs.get(tool.code)
    if config is None or not config.online:
        raise HTTPException(status_code=400, detail="工具未上线")
    if effective_engine(tool, config) != "local":
        raise HTTPException(status_code=400, detail="服务端任务使用记录由系统自动写入")

    session.add(
        UsageRecord(
            tool_code=tool.code,
            tool_name=tool.name,
            result=payload.result,
            engine="local",
            duration_ms=payload.duration_ms,
            ip=client_ip(request),
            file_count=payload.file_count,
            total_size=payload.total_size,
            error_code=payload.error_code,
            is_retry=payload.is_retry,
        )
    )
    await session.commit()


class FeedbackContext(BaseModel):
    path: str | None = Field(default=None, max_length=500)
    tool_code: str | None = Field(default=None, max_length=16)
    task_id: str | None = Field(default=None, max_length=40)
    error_code: str | None = Field(default=None, max_length=24)
    browser: str | None = Field(default=None, max_length=200)
    viewport: str | None = Field(default=None, max_length=40)


class FeedbackCreate(BaseModel):
    type: str
    tool_code: str | None = Field(default=None, max_length=16)
    description: str = Field(min_length=10, max_length=2000)
    expected: str | None = Field(default=None, max_length=500)
    contact: str | None = Field(default=None, max_length=100)
    context: FeedbackContext = Field(default_factory=FeedbackContext)

    @field_validator("type")
    @classmethod
    def check_type(cls, value: str) -> str:
        if value not in FEEDBACK_TYPES:
            raise ValueError("未知的问题类型")
        return value

    @field_validator("description")
    @classmethod
    def check_description(cls, value: str) -> str:
        text = value.strip()
        if len(text) < 10:
            raise ValueError("问题描述至少需要 10 个字符")
        compact = re.sub(r"\s", "", text)
        if len(set(compact)) < 3:
            raise ValueError("请具体说明「做了什么、看到什么」，重复字符无法帮助我们定位问题")
        return text


def _next_feedback_number(session: AsyncSession, prefix: str) -> str:
    return prefix  # 占位，实际序号在插入时查询数据库


async def _feedback_sequence(session: AsyncSession, prefix: str) -> int:
    last = await session.scalar(
        select(Feedback.number).where(Feedback.number.like(f"{prefix}%")).order_by(Feedback.number.desc()).limit(1)
    )
    if not last:
        return 1
    try:
        return int(last.rsplit("-", 1)[-1]) + 1
    except ValueError:
        return 1


@router.post("/feedback", summary="提交问题反馈")
async def submit_feedback(
    payload: FeedbackCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    site_settings = await get_site_settings(session)
    if site_settings.get("feedback_enabled", "true") != "true":
        raise HTTPException(status_code=403, detail="反馈暂不可用")

    ip = client_ip(request)
    redis = request.app.state.redis
    allowed, reset_at = await rate_limit(
        redis, f"startools:fb:rate:{ip}", settings.feedback_rate_per_hour, 3600
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "本小时反馈已达上限",
                "retry_at": reset_at.isoformat() if reset_at else None,
            },
        )

    tool_code = payload.tool_code if payload.tool_code not in {"", "unsure"} else None
    if tool_code and tool_code not in CODE_MAP:
        raise HTTPException(status_code=400, detail="关联工具不存在")

    duplicate = duplicate_key(ip, tool_code, payload.description)
    if not await reserve_duplicate_key(redis, duplicate, settings.feedback_duplicate_minutes * 60):
        raise HTTPException(status_code=409, detail="已收到相同反馈，无需重复提交")

    now = datetime.now(UTC)
    local_date = now.astimezone(ZoneInfo(settings.site_timezone)).strftime("%Y%m%d")
    prefix = f"FB-{local_date}-"

    context = payload.context.model_dump()
    if context.get("path"):
        context["path"] = urlsplit(context["path"]).path
    context["submitted_at"] = now.isoformat()
    context["ip"] = ip

    feedback: Feedback | None = None
    for _ in range(3):
        sequence = await _feedback_sequence(session, prefix)
        feedback = Feedback(
            number=f"{prefix}{sequence:04d}",
            type=payload.type,
            tool_code=tool_code,
            description=payload.description,
            expected=(payload.expected or "").strip() or None,
            contact=(payload.contact or "").strip() or None,
            context=context,
            ip=ip,
            status="pending",
        )
        session.add(feedback)
        try:
            await session.flush()
            break
        except Exception:
            await session.rollback()
            feedback = None
    if feedback is None:
        raise HTTPException(status_code=500, detail="反馈编号生成失败，请重试")

    session.add(
        FeedbackEvent(
            feedback_id=feedback.id,
            kind="status",
            from_status=None,
            to_status="pending",
            actor="访客",
        )
    )
    await session.commit()

    return {
        "number": feedback.number,
        "created_at": feedback.created_at.isoformat(),
        "message": "已收到你的反馈，维护者会在管理台查看。",
    }

"""过期清理：启动时补清理一次，之后每日执行。"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.models import (
    AuditRecord,
    Feedback,
    FeedbackEvent,
    RawFile,
    ResultItem,
    ServerTask,
    UsageRecord,
)
from app.services.common import cleanup_dir

logger = logging.getLogger(__name__)


async def cleanup_expired(factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    now = datetime.now(UTC)
    counts = {"raw": 0, "results": 0, "tasks": 0, "usage": 0, "feedback": 0, "audit": 0}

    async with factory() as session:
        raw_rows = (await session.scalars(select(RawFile).where(RawFile.expires_at < now))).all()
        task_ids: set[str] = set()
        for row in raw_rows:
            cleanup_dir(settings.raw_path / row.task_id)
            task_ids.add(row.task_id)
            await session.delete(row)
            counts["raw"] += 1

        result_rows = (await session.scalars(select(ResultItem).where(ResultItem.expires_at < now))).all()
        result_task_ids: set[str] = set()
        for row in result_rows:
            cleanup_dir(settings.result_path / row.task_id)
            result_task_ids.add(row.task_id)
            await session.delete(row)
            counts["results"] += 1

        task_rows = (
            await session.scalars(
                select(ServerTask).where(ServerTask.expires_at < now, ServerTask.expires_at.is_not(None))
            )
        ).all()
        for row in task_rows:
            await session.delete(row)
            counts["tasks"] += 1

        cutoff = now - timedelta(days=settings.record_retention_days)
        usage_deleted = await session.execute(delete(UsageRecord).where(UsageRecord.created_at < cutoff))
        counts["usage"] = usage_deleted.rowcount or 0

        old_feedback = (await session.scalars(select(Feedback).where(Feedback.created_at < cutoff))).all()
        for row in old_feedback:
            await session.execute(delete(FeedbackEvent).where(FeedbackEvent.feedback_id == row.id))
            await session.delete(row)
            counts["feedback"] += 1

        audit_deleted = await session.execute(delete(AuditRecord).where(AuditRecord.created_at < cutoff))
        counts["audit"] = audit_deleted.rowcount or 0

        await session.commit()

    for task_id in task_ids:
        cleanup_dir(settings.raw_path / task_id)
        cleanup_dir(settings.result_path / task_id)

    logger.info("过期数据清理完成：%s", counts)
    return counts


async def cleanup_loop(factory: async_sessionmaker[AsyncSession]) -> None:
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            await cleanup_expired(factory)
        except Exception:  # pragma: no cover - 后台任务不阻塞主服务
            logger.exception("每日清理失败")

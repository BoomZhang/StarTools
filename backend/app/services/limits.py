"""限流、存储保护与审计写入。"""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditRecord


async def rate_limit(
    redis, key: str, limit: int, window_seconds: int
) -> tuple[bool, datetime | None]:
    """固定窗口计数；超限时返回恢复时间。"""
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    if count > limit:
        ttl = await redis.ttl(key)
        ttl = ttl if ttl and ttl > 0 else window_seconds
        return False, datetime.now(UTC) + timedelta(seconds=ttl)
    return True, None


async def reserve_duplicate_key(redis, key: str, ttl_seconds: int) -> bool:
    """重复提交判定：键不存在时写入并返回 True，已存在返回 False。"""
    return bool(await redis.set(key, "1", nx=True, ex=ttl_seconds))


def duplicate_key(ip: str, tool_code: str | None, description: str) -> str:
    digest = hashlib.sha256(description.strip().encode("utf-8")).hexdigest()[:24]
    return f"startools:fb:dup:{ip}:{tool_code or 'none'}:{digest}"


async def lock_login(redis, ip: str, username: str, max_failures: int, minutes: int) -> tuple[bool, datetime | None]:
    """连续失败达到阈值后锁定；返回当前是否被锁定与恢复时间。"""
    fail_key = f"startools:login:fail:{ip}:{username}"
    lock_key = f"startools:login:lock:{ip}:{username}"

    ttl = await redis.ttl(lock_key)
    if ttl and ttl > 0:
        return True, datetime.now(UTC) + timedelta(seconds=ttl)

    failures = int(await redis.get(fail_key) or 0)
    if failures >= max_failures:
        await redis.set(lock_key, "1", ex=minutes * 60)
        await redis.delete(fail_key)
        return True, datetime.now(UTC) + timedelta(minutes=minutes)
    return False, None


async def record_login_failure(redis, ip: str, username: str, max_failures: int, minutes: int) -> None:
    key = f"startools:login:fail:{ip}:{username}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, minutes * 60)
    if count >= max_failures:
        await redis.set(f"startools:login:lock:{ip}:{username}", "1", ex=minutes * 60)
        await redis.delete(key)


async def clear_login_failures(redis, ip: str, username: str) -> None:
    await redis.delete(f"startools:login:fail:{ip}:{username}")


def write_audit(
    session: AsyncSession,
    actor: str,
    action: str,
    target: str,
    detail: dict,
    ip: str,
) -> None:
    session.add(
        AuditRecord(
            actor=actor,
            action=action,
            target=target,
            detail=detail,
            ip=ip,
        )
    )

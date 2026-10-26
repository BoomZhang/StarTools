import asyncio
import time
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app import __version__
from app.core.config import settings
from app.services.common import tesseract_available

router = APIRouter(tags=["system"])


class CheckResult(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    env: str
    time: datetime
    checks: dict[str, CheckResult]


def _error_detail(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:200]


async def _check_database(engine) -> CheckResult:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(settings.check_timeout):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        return CheckResult(status="down", detail=_error_detail(exc))
    return CheckResult(status="up", latency_ms=round((time.perf_counter() - started) * 1000, 2))


async def _check_redis(client) -> CheckResult:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(settings.check_timeout):
            await client.ping()
    except Exception as exc:
        return CheckResult(status="down", detail=_error_detail(exc))
    return CheckResult(status="up", latency_ms=round((time.perf_counter() - started) * 1000, 2))


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
async def health(request: Request) -> HealthResponse:
    database, cache = await asyncio.gather(
        _check_database(request.app.state.db_engine),
        _check_redis(request.app.state.redis),
    )
    checks = {
        "database": database,
        "redis": cache,
        "ocr": CheckResult(
            status="up" if tesseract_available() else "down",
            detail=None if tesseract_available() else "Tesseract 引擎未安装，OCR-01 将显示不可用",
        ),
    }
    overall = "ok" if all(item.status == "up" for item in checks.values()) else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        version=__version__,
        env=settings.app_env,
        time=datetime.now(UTC),
        checks=checks,
    )

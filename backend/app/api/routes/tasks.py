"""服务端任务：上传、校验、处理、会话恢复与结果下载。"""

import asyncio
import json
import shutil
import time
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.catalog import CODE_MAP
from app.core.clients import get_db
from app.core.config import settings
from app.db.models import RawFile, ResultItem, ServerTask, UsageRecord, new_id
from app.services.common import (
    client_ip,
    disk_accepts_tasks,
    safe_stem,
    timestamp_label,
    unique_filename,
)
from app.services.config_service import effective_engine, load_configs
from app.services.limits import rate_limit
from app.services.runner import availability, run_processor
from app.services.types import FileResult, TaskError, TextResult

router = APIRouter(tags=["tasks"])

MB = 1024 * 1024


def _serialize_task(task: ServerTask, results: list[ResultItem]) -> dict:
    now = datetime.now(UTC)
    expired = bool(task.expires_at and task.expires_at <= now)
    status = "expired" if expired and task.status in {"succeeded", "partial"} else task.status
    payload = {
        "task_id": task.id,
        "tool_code": task.tool_code,
        "status": status,
        "engine": task.engine,
        "file_count": task.file_count,
        "total_size": task.total_size,
        "duration_ms": task.duration_ms,
        "created_at": task.created_at.isoformat(),
        "expires_at": task.expires_at.isoformat() if task.expires_at else None,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "notes": task.notes or [],
        "failures": task.failures or [],
        "results": [],
    }
    if not expired:
        payload["results"] = [
            {
                "id": item.id,
                "filename": item.filename,
                "size": item.size,
                "content_type": item.content_type,
                "kind": item.kind,
                "text": item.text_content if item.kind == "text" else None,
                "meta": item.meta or {},
                "expires_at": item.expires_at.isoformat(),
                "download_url": f"{settings.api_prefix}/tasks/{task.id}/results/{item.id}",
                "preview_url": (
                    f"{settings.api_prefix}/tasks/{task.id}/results/{item.id}?inline=1"
                    if item.content_type.startswith("image/")
                    else None
                ),
            }
            for item in results
            if not item.deleted
        ]
    return payload


async def _active_results(session: AsyncSession, task_id: str) -> list[ResultItem]:
    return list(
        (
            await session.scalars(
                select(ResultItem).where(ResultItem.task_id == task_id, ResultItem.deleted.is_(False))
            )
        ).all()
    )


def _usage(
    tool_code: str,
    tool_name: str,
    status: str,
    duration_ms: int,
    ip: str,
    file_count: int,
    total_size: int,
    error_code: str | None,
    is_retry: bool,
) -> UsageRecord:
    return UsageRecord(
        tool_code=tool_code,
        tool_name=tool_name,
        result=status,
        engine="server",
        duration_ms=duration_ms,
        ip=ip,
        file_count=file_count,
        total_size=total_size,
        error_code=error_code,
        is_retry=is_retry,
    )


def _sanitize_params(tool_code: str, params: dict) -> dict:
    """任务参数落库前移除密码与文本内容。"""
    clean = dict(params)
    if tool_code == "DOC-09":
        clean.pop("password", None)
        clean["password_set"] = True
    elif tool_code == "AV-07":
        text = str(clean.pop("text", ""))
        clean["chars"] = len(text)
    return clean


@router.post("/tasks", summary="创建服务端处理任务")
async def create_task(
    request: Request,
    tool_code: str = Form(...),
    params: str = Form("{}"),
    is_retry: bool = Form(False),
    files: list[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_db),
):
    tool = CODE_MAP.get(tool_code)
    if tool is None or not tool.implemented:
        raise HTTPException(status_code=404, detail="工具不存在")

    configs = await load_configs(session)
    config = configs.get(tool.code)
    if config is None or not config.online:
        raise HTTPException(status_code=410, detail={"code": "E7-410", "message": "该工具已被维护者下线"})

    available, reason = availability(tool)
    if not available:
        raise HTTPException(status_code=503, detail={"code": "E4-503", "message": reason})

    engine = effective_engine(tool, config)
    if engine != "server":
        raise HTTPException(
            status_code=409,
            detail={"code": "E7-409", "message": "处理方式已更新，请刷新页面后重试"},
        )
    if not disk_accepts_tasks():
        raise HTTPException(
            status_code=503,
            detail={"code": "E4-503", "message": "服务端任务暂不可用，前端工具正常"},
        )

    try:
        parsed_params = json.loads(params or "{}")
        if not isinstance(parsed_params, dict):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "E1-400", "message": "参数格式不合法"}) from exc

    if tool.code == "AV-07":
        text = str(parsed_params.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail={"code": "E1-400", "message": "请输入要合成的文本"})
        if len(text) > 5000:
            raise HTTPException(
                status_code=413,
                detail={"code": "E2-413", "message": f"文本 {len(text)} 字符，上限 5000 字符"},
            )

    max_count = config.max_count or 1
    max_size = (config.max_file_mb or 0) * MB
    if tool.accepts_files:
        if len(files) < 1:
            raise HTTPException(status_code=400, detail={"code": "E1-400", "message": "请至少添加 1 个文件"})
        allowed_count = max_count + (
            1 if tool.code == "IMG-04" and str(parsed_params.get("mode", "text")) == "image" else 0
        )
        if len(files) > allowed_count:
            raise HTTPException(
                status_code=413,
                detail={"code": "E2-413", "message": f"单次最多 {allowed_count} 个文件，当前 {len(files)} 个"},
            )
        if max_size <= 0:
            raise HTTPException(status_code=400, detail={"code": "E1-400", "message": "该工具未配置单文件上限"})
        for upload in files:
            if upload.size is not None and upload.size > max_size:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "code": "E2-413",
                        "message": f"{upload.filename} 为 {upload.size / MB:.1f}MB，单文件上限 {config.max_file_mb}MB",
                    },
                )
    elif files:
        raise HTTPException(status_code=400, detail={"code": "E1-400", "message": "该工具不接受文件输入"})

    ip = client_ip(request)
    redis = request.app.state.redis
    allowed, reset_at = await rate_limit(
        redis, f"startools:task:{ip}", settings.server_task_rate_per_hour, 3600
    )
    if not allowed:
        retry_label = reset_at.astimezone().strftime("%H:%M") if reset_at else "稍后"
        raise HTTPException(
            status_code=429,
            detail={
                "code": "E2-429",
                "message": f"本小时服务端任务已达 {settings.server_task_rate_per_hour} 次，预计 {retry_label} 恢复",
            },
        )

    task_id = new_id()
    raw_dir = settings.raw_path / task_id
    result_dir = settings.result_path / task_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    saved_paths: list[Path] = []
    saved_names: list[str] = []
    used_names: set[str] = set()
    total_size = 0

    try:
        for upload in files:
            display_name = f"{safe_stem(upload.filename or 'file')}{Path(upload.filename or '').suffix.lower()}"
            stored_name = unique_filename(display_name, used_names)
            target = raw_dir / stored_name
            size = 0
            with target.open("wb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_size:
                        raise HTTPException(
                            status_code=413,
                            detail={
                                "code": "E2-413",
                                "message": f"{upload.filename} 超过单文件上限 {config.max_file_mb}MB",
                            },
                        )
                    handle.write(chunk)
            if size == 0:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "E1-400", "message": f"{upload.filename} 是空文件，无法处理"},
                )
            total_size += size
            saved_paths.append(target)
            saved_names.append(display_name or stored_name)
            session.add(
                RawFile(
                    task_id=task_id,
                    tool_code=tool.code,
                    filename=upload.filename or stored_name,
                    stored_path=str(target),
                    content_type=upload.content_type or "application/octet-stream",
                    size=size,
                    ip=ip,
                    expires_at=datetime.now(UTC) + timedelta(days=settings.raw_retention_days),
                )
            )
    except HTTPException:
        shutil.rmtree(raw_dir, ignore_errors=True)
        shutil.rmtree(result_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(raw_dir, ignore_errors=True)
        shutil.rmtree(result_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail={"code": "E1-400", "message": f"文件保存失败：{exc}"}) from exc

    task = ServerTask(
        id=task_id,
        tool_code=tool.code,
        status="processing",
        engine="server",
        file_count=len(saved_paths),
        total_size=total_size,
        ip=ip,
        params=_sanitize_params(tool.code, parsed_params),
    )
    session.add(task)
    await session.flush()

    try:
        outcome = await asyncio.to_thread(
            run_processor, tool.code, saved_paths, saved_names, parsed_params, result_dir
        )
    except TaskError as exc:
        await _finish_failure(session, task, exc.code, exc.message, started, ip, is_retry, tool.name)
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message, "task_id": task.id},
        ) from exc
    except Exception as exc:  # pragma: no cover
        await _finish_failure(session, task, "E4-500", "处理服务异常，请稍后重试", started, ip, is_retry, tool.name)
        raise HTTPException(
            status_code=500,
            detail={"code": "E4-500", "message": "处理服务异常，请稍后重试", "task_id": task.id},
        ) from exc

    duration_ms = int((time.perf_counter() - started) * 1000)
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.result_retention_minutes)
    task.status = outcome.status
    task.duration_ms = duration_ms
    task.completed_at = now
    task.expires_at = expires_at
    task.notes = outcome.notes
    task.failures = outcome.failures

    stored_results: list[ResultItem] = []
    for item in outcome.results:
        if isinstance(item, TextResult):
            path = result_dir / item.filename
            path.write_text(item.text, encoding="utf-8")
            row = ResultItem(
                task_id=task.id,
                filename=item.filename,
                stored_path=str(path),
                content_type="text/plain; charset=utf-8",
                size=path.stat().st_size,
                kind="text",
                text_content=item.text,
                meta=item.meta,
                expires_at=expires_at,
            )
        else:
            assert isinstance(item, FileResult)
            row = ResultItem(
                task_id=task.id,
                filename=item.filename,
                stored_path=str(item.path),
                content_type=item.content_type,
                size=item.path.stat().st_size,
                kind="file",
                meta=item.meta,
                expires_at=expires_at,
            )
        session.add(row)
        stored_results.append(row)

    first_error = outcome.failures[0]["code"] if outcome.failures else None
    session.add(
        _usage(
            tool.code, tool.name, outcome.status, duration_ms, ip, len(saved_paths), total_size, first_error, is_retry
        )
    )
    await session.commit()
    await session.refresh(task)
    for row in stored_results:
        await session.refresh(row)

    return _serialize_task(task, stored_results)


async def _finish_failure(
    session: AsyncSession,
    task: ServerTask,
    code: str,
    message: str,
    started: float,
    ip: str,
    is_retry: bool,
    tool_name: str,
) -> None:
    duration_ms = int((time.perf_counter() - started) * 1000)
    now = datetime.now(UTC)
    task.status = "failed"
    task.duration_ms = duration_ms
    task.completed_at = now
    task.expires_at = now + timedelta(minutes=settings.result_retention_minutes)
    task.error_code = code
    task.error_message = message
    session.add(
        _usage(task.tool_code, tool_name, "failed", duration_ms, ip, task.file_count, task.total_size, code, is_retry)
    )
    await session.commit()


@router.get("/tasks/{task_id}", summary="恢复任务状态与结果")
async def get_task(task_id: str, session: AsyncSession = Depends(get_db)) -> dict:
    task = await session.get(ServerTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已被清理")
    results = await _active_results(session, task_id)
    return _serialize_task(task, results)


@router.get("/tasks/{task_id}/results/{result_id}", summary="下载结果")
async def download_result(
    task_id: str, result_id: str, inline: bool = False, session: AsyncSession = Depends(get_db)
):
    item = await session.get(ResultItem, result_id)
    if item is None or item.task_id != task_id or item.deleted:
        raise HTTPException(status_code=404, detail="结果不存在")
    if item.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="结果已过期，请重新处理")
    if not item.stored_path or not Path(item.stored_path).exists():
        raise HTTPException(status_code=410, detail="结果文件已不可用，请重新处理")
    if inline:
        return FileResponse(
            item.stored_path,
            media_type=item.content_type,
            headers={"Content-Disposition": "inline", "Cache-Control": "no-store"},
        )
    return FileResponse(
        item.stored_path,
        filename=item.filename,
        media_type=item.content_type,
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/tasks/{task_id}/results", status_code=200, summary="删除结果")
async def delete_results(task_id: str, session: AsyncSession = Depends(get_db)) -> dict:
    results = await _active_results(session, task_id)
    for item in results:
        if item.stored_path:
            Path(item.stored_path).unlink(missing_ok=True)
        item.deleted = True
    await session.commit()
    return {"deleted": len(results)}


@router.get("/tasks/{task_id}/archive", summary="批量打包下载结果")
async def archive_results(task_id: str, session: AsyncSession = Depends(get_db)):
    task = await session.get(ServerTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    results = await _active_results(session, task_id)
    if not results:
        raise HTTPException(status_code=404, detail="没有可下载的结果")

    tool = CODE_MAP.get(task.tool_code)
    archive_dir = settings.result_path / task_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{safe_stem(tool.name if tool else '结果')}_{timestamp_label()}.zip"
    archive_path = archive_dir / archive_name

    used: set[str] = set()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in results:
            if not item.stored_path or not Path(item.stored_path).exists():
                continue
            name = unique_filename(item.filename, used)
            archive.write(item.stored_path, arcname=name)

    return FileResponse(
        archive_path,
        filename=archive_name,
        media_type="application/zip",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(lambda: archive_path.unlink(missing_ok=True)),
    )

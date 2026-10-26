"""跨处理器共用的文件名、打包、IP 与能力探测工具。"""

import re
import shutil
import unicodedata
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request

from app.core.config import settings

_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_CONTROL = re.compile(r"[\x00-\x1f]")


def safe_stem(filename: str, fallback: str = "result") -> str:
    stem = Path(filename).stem or fallback
    stem = unicodedata.normalize("NFC", stem)
    stem = _INVALID_FILENAME.sub("_", stem)
    stem = stem.strip(" .") or fallback
    return stem[:120]


def unique_filename(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem, dot, suffix = name.rpartition(".")
    stem = stem or name
    suffix = dot + suffix if dot else ""
    index = 2
    while f"{stem} ({index}){suffix}" in used:
        index += 1
    final = f"{stem} ({index}){suffix}"
    used.add(final)
    return final


def timestamp_label() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M")


def build_zip(paths: list[tuple[Path, str]], target: Path) -> Path:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, name in paths:
            archive.write(path, arcname=name)
    return target


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def disk_usage_percent() -> int:
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(settings.storage_path)
    return round(usage.used / usage.total * 100)


def disk_accepts_tasks() -> bool:
    return disk_usage_percent() < settings.disk_stop_percent


def normalize_ranges(expression: str) -> list[tuple[int, int] | int]:
    """把「1-3,5,8-10」解析为页码片段；支持全角逗号、顿号与连字符。"""
    cleaned = (
        expression.replace("，", ",")
        .replace("、", ",")
        .replace("－", "-")
        .replace("—", "-")
        .replace("–", "-")
        .replace(" ", "")
        .strip()
    )
    if not cleaned:
        return []
    parts: list[tuple[int, int] | int] = []
    for raw in cleaned.split(","):
        if not raw:
            continue
        if "-" in raw:
            left, _, right = raw.partition("-")
            if not left.isdigit() or not right.isdigit():
                raise ValueError(raw)
            start, end = int(left), int(right)
            if start < 1 or end < 1 or start > end:
                raise ValueError(raw)
            parts.append((start, end))
        elif raw.isdigit():
            if int(raw) < 1:
                raise ValueError(raw)
            parts.append(int(raw))
        else:
            raise ValueError(raw)
    return parts


def expand_ranges(parts: list[tuple[int, int] | int], total: int) -> list[int]:
    pages: list[int] = []
    for part in parts:
        start, end = (part, part) if isinstance(part, int) else part
        if start > total or end > total:
            raise ValueError(f"{start}-{end}")
        pages.extend(range(start, end + 1))
    return pages


def cleanup_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)

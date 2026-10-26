"""图片处理：格式转换、压缩与尺寸调整，服务端统一移除 EXIF 与拍摄信息。"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.common import safe_stem, unique_filename
from app.services.types import FileResult, ProcessOutcome, TaskError

try:  # HEIC 解码
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover - 环境缺失时明确报错
    pillow_heif = None

try:
    import cairosvg
except Exception:  # pragma: no cover
    cairosvg = None

# Pillow 采用惰性插件注册；先初始化再判断可编码格式
Image.init()

MAX_PIXELS = 80_000_000
FORMATS = {
    "jpg": ("JPEG", ".jpg", "image/jpeg"),
    "jpeg": ("JPEG", ".jpg", "image/jpeg"),
    "png": ("PNG", ".png", "image/png"),
    "webp": ("WEBP", ".webp", "image/webp"),
    "avif": ("AVIF", ".avif", "image/avif"),
    "gif": ("GIF", ".gif", "image/gif"),
    "bmp": ("BMP", ".bmp", "image/bmp"),
    "tiff": ("TIFF", ".tiff", "image/tiff"),
}
PRESETS = {
    "1080x1080": (1080, 1080),
    "1920x1080": (1920, 1080),
    "1280x720": (1280, 720),
    "750x1000": (750, 1000),
}


def available_output_formats() -> list[str]:
    return [
        fmt
        for fmt in ("jpg", "png", "webp", "avif", "gif", "bmp", "tiff")
        if FORMATS[fmt][0] in Image.SAVE
    ]


def _normalize_format(value: str) -> str:
    fmt = (value or "jpg").lower()
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in FORMATS:
        raise TaskError("E1-400", f"不支持的输出格式：{value}", 400)
    if FORMATS[fmt][0] not in Image.SAVE:
        raise TaskError("E6-415", f"当前服务端无法编码 {fmt.upper()}，请选择其他格式", 415)
    return fmt


def _hex_color(value: str) -> tuple[int, int, int]:
    text = (value or "#FFFFFF").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        return (255, 255, 255)
    try:
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (255, 255, 255)


def _open_image(path: Path, filename: str) -> Image.Image:
    suffix = Path(filename).suffix.lower()
    if suffix == ".svg":
        if cairosvg is None:
            raise TaskError("E6-415", "服务端缺少 SVG 栅格化能力，请改用其他格式", 415)
        try:
            png_bytes = cairosvg.svg2png(url=str(path), output_width=1024)
        except Exception as exc:
            raise TaskError("E3-422", "SVG 解析失败，请检查文件内容") from exc
        return Image.open(BytesIO(png_bytes))

    try:
        image = Image.open(path)
        image.seek(0)
        image.load()
    except UnidentifiedImageError as exc:
        raise TaskError("E1-400", f"{filename} 无法读取，文件可能已损坏或格式不支持") from exc
    except Exception as exc:
        if "heif" in str(exc).lower() or "heic" in str(exc).lower():
            raise TaskError("E6-415", "当前服务端无法解码 HEIC，请换用 JPG 或 PNG") from exc
        raise TaskError("E3-422", f"{filename} 解码失败") from exc

    if image.width * image.height > MAX_PIXELS:
        raise TaskError("E1-400", f"{filename} 超过 80MP 像素上限，请先缩小尺寸")

    image = ImageOps.exif_transpose(image)
    return image


def _flatten(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, background)
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        return canvas
    return image.convert("RGB")


def _save(
    image: Image.Image,
    target: Path,
    fmt: str,
    quality: int,
    background: tuple[int, int, int],
) -> None:
    pillow_format, _, _ = FORMATS[fmt]
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt in {"jpg", "avif", "bmp"}:
        image = _flatten(image, background)
    elif fmt == "gif":
        image = image.convert("RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    elif fmt in {"png", "webp", "tiff"}:
        image = image.convert("RGBA") if image.mode not in {"RGB", "RGBA", "L"} else image

    kwargs: dict = {}
    if fmt == "jpg":
        kwargs.update(quality=quality, optimize=True, progressive=True)
    elif fmt == "webp":
        kwargs.update(quality=quality, method=6)
    elif fmt == "avif":
        kwargs.update(quality=quality)
    elif fmt == "png":
        kwargs.update(optimize=True)
    elif fmt == "tiff":
        kwargs.update(compression="tiff_lzw")
    elif fmt == "gif":
        kwargs.update(optimize=True)

    image.save(target, format=pillow_format, **kwargs)


def _output_name(original: str, fmt: str, used: set[str]) -> str:
    _, ext, _ = FORMATS[fmt]
    return unique_filename(f"{safe_stem(original)}{ext}", used)


def process_image_convert(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    fmt = _normalize_format(str(params.get("format", "jpg")))
    quality = max(60, min(100, int(params.get("quality", 90) or 90)))
    background = _hex_color(str(params.get("background", "#FFFFFF")))
    outcome = ProcessOutcome()
    used: set[str] = set()

    for path, name in zip(files, names):
        try:
            image = _open_image(path, name)
            target = workdir / _output_name(name, fmt, used)
            _save(image, target, fmt, quality, background)
            outcome.results.append(
                FileResult(
                    filename=target.name,
                    path=target,
                    content_type=FORMATS[fmt][2],
                    meta={
                        "original_name": name,
                        "original_size": path.stat().st_size,
                        "new_size": target.stat().st_size,
                        "format": fmt,
                        "exif_removed": True,
                    },
                )
            )
        except TaskError as exc:
            outcome.failures.append({"filename": name, "code": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": name, "code": "E3-422", "message": f"{name} 转换失败：{exc}"})

    if outcome.results:
        outcome.notes.append("已移除拍摄信息（EXIF / GPS）。")
    return outcome


def process_image_compress(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    mode = str(params.get("mode", "quality"))
    quality = max(1, min(100, int(params.get("quality", 80) or 80)))
    allow_webp = bool(params.get("allow_webp", True))
    outcome = ProcessOutcome()
    used: set[str] = set()

    for path, name in zip(files, names):
        try:
            original_size = path.stat().st_size
            suffix = Path(name).suffix.lower().lstrip(".")
            can_webp = allow_webp and "WEBP" in Image.SAVE
            source_fmt = suffix if suffix in FORMATS else "jpg"
            note = ""

            if mode == "target":
                target_kb = float(params.get("target_kb", 200) or 200)
                target_bytes = int(target_kb * 1024)
                if target_bytes >= original_size:
                    raise TaskError("E1-400", "目标大小不小于原文件，无需压缩", 400)
                fmt = "webp" if source_fmt == "png" and can_webp else source_fmt
                image = _open_image(path, name)
                best: tuple[int, Path, int] | None = None
                chosen: tuple[int, Path, int] | None = None
                for attempt in range(90, 39, -5):
                    candidate = workdir / f".attempt-{attempt}.{fmt}"
                    _save(image, candidate, fmt, attempt, (255, 255, 255))
                    size = candidate.stat().st_size
                    if best is None or size < best[2]:
                        best = (attempt, candidate, size)
                    if size <= target_bytes:
                        chosen = (attempt, candidate, size)
                        break
                if chosen is None:
                    chosen = best
                    note = "已接近极限，未能完全达到目标大小。"
                assert chosen is not None
                quality_used, candidate, new_size = chosen
                final = workdir / _output_name(name, fmt, used)
                candidate.replace(final)
                for leftover in workdir.glob(".attempt-*"):
                    leftover.unlink(missing_ok=True)
                if fmt == "webp" and source_fmt == "png":
                    note = (note + " 已转为 WebP。").strip()
                meta = {
                    "original_name": name,
                    "original_size": original_size,
                    "new_size": new_size,
                    "format": fmt,
                    "quality": quality_used,
                    "mode": mode,
                    "note": note,
                }
            else:
                image = _open_image(path, name)
                fmt = source_fmt
                candidate = workdir / _output_name(name, fmt, used)
                _save(image, candidate, fmt, quality, (255, 255, 255))
                new_size = candidate.stat().st_size
                if new_size >= original_size:
                    # 压缩无收益：返回原文件，标记「已是最优」
                    candidate.unlink(missing_ok=True)
                    final = workdir / unique_filename(name, used)
                    final.write_bytes(path.read_bytes())
                    new_size = original_size
                    note = "已是最优，保留原文件。"
                else:
                    final = candidate
                meta = {
                    "original_name": name,
                    "original_size": original_size,
                    "new_size": new_size,
                    "format": fmt,
                    "quality": quality,
                    "mode": mode,
                    "note": note or None,
                }

            ratio = round((1 - new_size / original_size) * 100, 1) if original_size else 0
            meta["ratio"] = ratio
            outcome.results.append(
                FileResult(
                    filename=final.name,
                    path=final,
                    content_type=FORMATS[fmt][2],
                    meta=meta,
                )
            )
        except TaskError as exc:
            outcome.failures.append({"filename": name, "code": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": name, "code": "E3-422", "message": f"{name} 压缩失败：{exc}"})

    if any(item.meta.get("note") == "已是最优，保留原文件。" for item in outcome.results if isinstance(item, FileResult)):
        outcome.notes.append("部分图片已是最优，保留原文件。")
    return outcome


def _crop_ratios(params: dict) -> tuple[float, float, float, float] | None:
    keys = ("crop_x", "crop_y", "crop_width", "crop_height")
    if any(params.get(key) in (None, "") for key in keys):
        return None
    try:
        x, y, crop_w, crop_h = (float(params[key]) for key in keys)
    except (TypeError, ValueError) as exc:
        raise TaskError("E1-400", "裁剪参数不合法，请重新框选区域") from exc
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < crop_w <= 1 and 0 < crop_h <= 1):
        raise TaskError("E1-400", "裁剪参数不合法，请重新框选区域")
    if x + crop_w > 1.001 or y + crop_h > 1.001:
        raise TaskError("E1-400", "裁剪区域超出图片范围，请重新框选")
    return x, y, crop_w, crop_h


def process_image_resize(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    mode = str(params.get("mode", "pixel"))
    fit = str(params.get("fit", "contain"))
    background = _hex_color(str(params.get("background", "#FFFFFF")))
    quality = max(60, min(100, int(params.get("quality", 90) or 90)))
    output_format = str(params.get("format", "auto"))
    outcome = ProcessOutcome()
    used: set[str] = set()
    crop_ratios = _crop_ratios(params)

    width_param = params.get("width")
    height_param = params.get("height")
    percent = float(params.get("percent", 100) or 100)

    for path, name in zip(files, names):
        try:
            image = _open_image(path, name)
            original_w, original_h = image.size

            if crop_ratios is not None:
                crop_x, crop_y, crop_w, crop_h = crop_ratios
                left = max(0, min(original_w - 1, round(crop_x * original_w)))
                top = max(0, min(original_h - 1, round(crop_y * original_h)))
                right = max(left + 1, min(original_w, round((crop_x + crop_w) * original_w)))
                bottom = max(top + 1, min(original_h, round((crop_y + crop_h) * original_h)))
                image = image.crop((left, top, right, bottom))
                original_w, original_h = image.size

            if mode == "percent":
                if not 1 <= percent <= 400:
                    raise TaskError("E1-400", "缩放比例需在 1%–400% 之间")
                target_w = max(1, round(original_w * percent / 100))
                target_h = max(1, round(original_h * percent / 100))
            elif mode == "preset":
                preset = PRESETS.get(str(params.get("preset", "1080x1080")))
                if not preset:
                    raise TaskError("E1-400", "未知的常用尺寸")
                target_w, target_h = preset
            elif mode == "crop":
                target_w, target_h = original_w, original_h
            else:
                if width_param in (None, "") or height_param in (None, ""):
                    raise TaskError("E1-400", "请填写目标宽度与高度")
                target_w = int(width_param)
                target_h = int(height_param)
                if not (1 <= target_w <= 10000 and 1 <= target_h <= 10000):
                    raise TaskError("E1-400", "宽高需在 1–10000px 之间")

            if target_w * target_h > MAX_PIXELS:
                raise TaskError("E1-400", "目标像素超过 80MP 上限，请降低目标尺寸")

            if fit == "cover":
                resized = ImageOps.fit(image, (target_w, target_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            elif fit == "stretch":
                resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
            else:
                scale = min(target_w / original_w, target_h / original_h)
                new_w = max(1, round(original_w * scale))
                new_h = max(1, round(original_h * scale))
                scaled = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                resized = Image.new("RGBA", (target_w, target_h), (*background, 255))
                resized.paste(scaled.convert("RGBA"), ((target_w - new_w) // 2, (target_h - new_h) // 2))

            source_fmt = Path(name).suffix.lower().lstrip(".")
            if output_format == "auto":
                fmt = source_fmt if source_fmt in FORMATS else "jpg"
            else:
                fmt = output_format
            fmt = _normalize_format(fmt)

            final = workdir / _output_name(name, fmt, used)
            _save(resized, final, fmt, quality, background)
            upscale_note = "放大超过 200%，会明显损失清晰度。" if target_w * target_h > original_w * original_h * 4 else None
            outcome.results.append(
                FileResult(
                    filename=final.name,
                    path=final,
                    content_type=FORMATS[fmt][2],
                    meta={
                        "original_name": name,
                        "original_width": original_w,
                        "original_height": original_h,
                        "width": target_w,
                        "height": target_h,
                        "format": fmt,
                        "note": upscale_note,
                    },
                )
            )
        except TaskError as exc:
            outcome.failures.append({"filename": name, "code": exc.code, "message": exc.message})
        except (TypeError, ValueError):
            outcome.failures.append({"filename": name, "code": "E1-400", "message": f"{name} 的尺寸参数不合法"})
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": name, "code": "E3-422", "message": f"{name} 处理失败：{exc}"})

    if any(item.meta.get("note") for item in outcome.results if isinstance(item, FileResult)):
        outcome.notes.append("部分图片被放大，清晰度可能下降。")
    return outcome

"""图片 P1：加水印、拼接与图标生成。"""

import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.services.common import safe_stem, timestamp_label, unique_filename
from app.services.images import FORMATS, _open_image, _save
from app.services.types import FileResult, ProcessOutcome, TaskError

FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
)
POSITIONS = {
    "top-left": (0.04, 0.04, "left", "top"),
    "top-center": (0.5, 0.04, "center", "top"),
    "top-right": (0.96, 0.04, "right", "top"),
    "center-left": (0.04, 0.5, "left", "center"),
    "center": (0.5, 0.5, "center", "center"),
    "center-right": (0.96, 0.5, "right", "center"),
    "bottom-left": (0.04, 0.96, "left", "bottom"),
    "bottom-center": (0.5, 0.96, "center", "bottom"),
    "bottom-right": (0.96, 0.96, "right", "bottom"),
}


def _font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - 旧版 Pillow
        return ImageFont.load_default()


def _hex_rgba(value: str, opacity: int) -> tuple[int, int, int, int]:
    text = (value or "#FFFFFF").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6:
        text = "FFFFFF"
    try:
        rgb = tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        rgb = (255, 255, 255)
    alpha = round(max(5, min(100, opacity)) / 100 * 255)
    return (*rgb, alpha)  # type: ignore[return-value]


def _annotate(image: Image.Image, draw: callable, mode: str, params: dict) -> None:
    opacity = int(params.get("opacity", 60) or 60)
    position = str(params.get("position", "bottom-right"))
    tile = bool(params.get("tile", False))

    if mode == "text":
        text = str(params.get("text", "仅限内部使用")).strip() or "仅限内部使用"
        size = max(12, min(200, int(params.get("font_size", 36) or 36)))
        font = _font(size)
        color = _hex_rgba(str(params.get("color", "#FFFFFF")), opacity)
        width, height = image.size

        def draw_text_at(x: int, y: int) -> None:
            draw.text((x, y), text, font=font, fill=color, anchor="la")

        box = draw.textbbox((0, 0), text, font=font)
        text_w = box[2] - box[0]
        text_h = box[3] - box[1]

        if tile:
            margin = max(24, size // 2)
            step_x = text_w + margin * 2
            step_y = text_h + margin * 2
            for y in range(-text_h, height + step_y, step_y):
                for x in range(-text_w, width + step_x, step_x):
                    draw_text_at(x, y)
            return

        rx, ry, horizontal, vertical = POSITIONS.get(position, POSITIONS["bottom-right"])
        margin = max(12, int(min(width, height) * 0.04))
        x = int(width * rx) - (text_w if horizontal == "right" else text_w // 2 if horizontal == "center" else 0)
        y = int(height * ry) - (text_h if vertical == "bottom" else text_h // 2 if vertical == "center" else 0)
        x = max(margin, min(width - text_w - margin, x))
        y = max(margin, min(height - text_h - margin, y))
        draw_text_at(x, y)
        return

    watermark_path = params.get("_watermark_path")
    if not watermark_path:
        raise TaskError("E1-400", "图片水印模式需要额外上传一张水印图片")
    watermark = Image.open(watermark_path)
    watermark.seek(0)
    watermark.load()
    watermark = watermark.convert("RGBA")
    target_w = max(24, int(image.width * 0.2))
    ratio = target_w / watermark.width
    watermark = watermark.resize((target_w, max(1, int(watermark.height * ratio))), Image.Resampling.LANCZOS)

    alpha = watermark.getchannel("A").point(lambda value: round(value * opacity / 100))
    watermark.putalpha(alpha)
    margin = max(8, int(min(image.size) * 0.04))
    if tile:
        step_x = watermark.width + margin * 2
        step_y = watermark.height + margin * 2
        for y in range(-watermark.height, image.height + step_y, step_y):
            for x in range(-watermark.width, image.width + step_x, step_x):
                image.alpha_composite(watermark, (x, y))
        return

    rx, ry, horizontal, vertical = POSITIONS.get(position, POSITIONS["bottom-right"])
    x = int(image.width * rx) - (watermark.width if horizontal == "right" else watermark.width // 2 if horizontal == "center" else 0)
    y = int(image.height * ry) - (watermark.height if vertical == "bottom" else watermark.height // 2 if vertical == "center" else 0)
    x = max(margin, min(image.width - watermark.width - margin, x))
    y = max(margin, min(image.height - watermark.height - margin, y))
    image.alpha_composite(watermark, (x, y))


def process_image_watermark(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    mode = str(params.get("mode", "text"))
    watermark_last = bool(params.get("watermark_last", False))
    base_paths = files[:-1] if watermark_last else files
    base_names = names[:-1] if watermark_last else names
    if not base_paths:
        raise TaskError("E1-400", "请至少上传一张待加水印的图片")
    if watermark_last:
        watermark_path = files[-1]
        if watermark_path.stat().st_size > 2 * 1024 * 1024:
            raise TaskError("E2-413", "水印图片不能超过 2MB")
        params = {**params, "_watermark_path": str(watermark_path)}

    outcome = ProcessOutcome()
    used: set[str] = set()
    for path, name in zip(base_paths, base_names):
        try:
            image = _open_image(path, name)
            rgba = image.convert("RGBA")
            overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            _annotate(overlay, draw, mode, params)
            composed = Image.alpha_composite(rgba, overlay)
            suffix = Path(name).suffix.lower().lstrip(".")
            fmt = suffix if suffix in {"jpg", "jpeg", "png", "webp"} else "png"
            fmt = "jpg" if fmt == "jpeg" else fmt
            target = workdir / unique_filename(f"{safe_stem(name)}.{ 'jpg' if fmt == 'jpg' else fmt}", used)
            _save(composed, target, fmt, 92, (255, 255, 255))
            outcome.results.append(
                FileResult(
                    filename=target.name,
                    path=target,
                    content_type=FORMATS[fmt][2],
                    meta={
                        "original_name": name,
                        "width": composed.width,
                        "height": composed.height,
                        "format": fmt,
                        "mode": mode,
                    },
                )
            )
        except TaskError as exc:
            outcome.failures.append({"filename": name, "code": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": name, "code": "E3-422", "message": f"{name} 加水印失败：{exc}"})

    if outcome.results:
        outcome.notes.append("水印不超出画布；批量使用同一模板。")
    return outcome


def process_image_stitch(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    if len(files) < 2:
        raise TaskError("E1-400", "至少添加 2 张图片")
    direction = str(params.get("direction", "horizontal"))
    gap = max(0, min(50, int(params.get("gap", 8) or 8)))
    background = str(params.get("background", "#FFFFFF"))
    fmt = str(params.get("format", "png")).lower()
    fmt = "jpg" if fmt == "jpeg" else fmt
    if fmt not in {"jpg", "png", "webp"}:
        fmt = "png"
    quality = max(60, min(100, int(params.get("quality", 92) or 92)))

    images: list[Image.Image] = []
    used_names: list[str] = []
    for path, name in zip(files, names):
        try:
            images.append(_open_image(path, name).convert("RGBA"))
            used_names.append(name)
        except TaskError as exc:
            raise TaskError(exc.code, f"{name} 无法读取：{exc.message}") from exc

    if direction == "grid":
        columns = int(params.get("columns", 2))
        columns = 3 if columns >= 3 else 2
        cell = max(max(image.width, image.height) for image in images)
        rows = (len(images) + columns - 1) // columns
        width = columns * cell + gap * (columns - 1)
        height = rows * cell + gap * (rows - 1)
        canvas = Image.new("RGBA", (width, height), background)
        for index, image in enumerate(images):
            row, column = divmod(index, columns)
            thumb = ImageOps.contain(image, (cell, cell), Image.Resampling.LANCZOS)
            x = column * (cell + gap) + (cell - thumb.width) // 2
            y = row * (cell + gap) + (cell - thumb.height) // 2
            canvas.alpha_composite(thumb, (x, y))
    elif direction == "vertical":
        width = max(image.width for image in images)
        scaled = []
        for image in images:
            ratio = width / image.width
            scaled.append(image.resize((width, max(1, round(image.height * ratio))), Image.Resampling.LANCZOS))
        height = sum(image.height for image in scaled) + gap * (len(scaled) - 1)
        canvas = Image.new("RGBA", (width, height), background)
        y = 0
        for image in scaled:
            canvas.alpha_composite(image, (0, y))
            y += image.height + gap
    else:
        height = max(image.height for image in images)
        scaled = []
        for image in images:
            ratio = height / image.height
            scaled.append(image.resize((max(1, round(image.width * ratio)), height), Image.Resampling.LANCZOS))
        width = sum(image.width for image in scaled) + gap * (len(scaled) - 1)
        canvas = Image.new("RGBA", (width, height), background)
        x = 0
        for image in scaled:
            canvas.alpha_composite(image, (x, 0))
            x += image.width + gap

    if canvas.width * canvas.height > 80_000_000:
        scale = (80_000_000 / (canvas.width * canvas.height)) ** 0.5
        canvas = canvas.resize((max(1, round(canvas.width * scale)), max(1, round(canvas.height * scale))), Image.Resampling.LANCZOS)

    target = workdir / unique_filename(f"拼接_{timestamp_label()}.{ 'jpg' if fmt == 'jpg' else fmt}", set())
    _save(canvas, target, fmt, quality, (255, 255, 255))
    return ProcessOutcome(
        results=[
            FileResult(
                filename=target.name,
                path=target,
                content_type=FORMATS[fmt][2],
                meta={
                    "width": canvas.width,
                    "height": canvas.height,
                    "images": len(images),
                    "direction": direction,
                    "format": fmt,
                },
            )
        ],
        notes=["总输出像素不超过 80MP；超限时已自动等比缩小。"],
    )


def process_icon_generator(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    image = _open_image(path, name)
    if image.width < 256 or image.height < 256:
        raise TaskError("E1-400", "源图需不小于 256×256")
    square = ImageOps.fit(image.convert("RGBA"), (256, 256), Image.Resampling.LANCZOS)
    sizes = (16, 32, 48, 64, 128, 256)
    stem = safe_stem(name)
    paths: list[tuple[Path, str]] = []
    for size in sizes:
        target = workdir / f"{stem}_{size}.png"
        square.resize((size, size), Image.Resampling.LANCZOS).save(target, format="PNG", optimize=True)
        paths.append((target, target.name))
    ico = workdir / f"{stem}.ico"
    square.save(ico, format="ICO", sizes=[(size, size) for size in sizes])
    paths.append((ico, ico.name))
    zip_path = workdir / unique_filename(f"图标_{timestamp_label()}.zip", set())
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in paths:
            archive.write(source, arcname)
    for source, _ in paths:
        source.unlink(missing_ok=True)
    return ProcessOutcome(
        results=[
            FileResult(
                filename=zip_path.name,
                path=zip_path,
                content_type="application/zip",
                meta={"sizes": list(sizes), "files": len(paths)},
            )
        ],
        notes=["ZIP 内含 16–256 px 的 6 个 PNG 与一个多尺寸 ICO。"],
    )

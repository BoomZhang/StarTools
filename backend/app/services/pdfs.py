"""PDF 处理：图片合成、合并、拆分与转图。"""

from io import BytesIO
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter

from app.services.common import (
    expand_ranges,
    normalize_ranges,
    safe_stem,
    timestamp_label,
    unique_filename,
)
from app.services.types import FileResult, ProcessOutcome, TaskError

PAGE_SIZES = {"a4": (595.0, 842.0), "letter": (612.0, 792.0)}
MARGINS = {"none": 0.0, "small": 28.35, "medium": 56.7}
MAX_TOTAL_PAGES = 500
MAX_RENDER_PAGES = 200


def _pdf_writer_from(path: Path) -> PdfReader:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise TaskError("E1-400", f"{path.name} 无法读取，文件可能已损坏") from exc
    if reader.is_encrypted:
        raise TaskError("E1-400", f"{path.name} 已加密，请先移除打开密码")
    if len(reader.pages) == 0:
        raise TaskError("E1-400", f"{path.name} 不含任何页面")
    return reader


def process_images_to_pdf(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    page_mode = str(params.get("page", "a4"))
    orientation = str(params.get("orientation", "auto"))
    margin_key = str(params.get("margin", "small"))
    margin = MARGINS.get(margin_key, MARGINS["small"])
    outcome = ProcessOutcome()

    document = fitz.open()
    used_pages = 0

    for path, name in zip(files, names):
        try:
            image = Image.open(path)
            image.seek(0)
            image.load()
            try:
                from PIL import ImageOps

                image = ImageOps.exif_transpose(image)
            except Exception:
                pass
            image = image.convert("RGB")

            if page_mode == "original":
                width = max(72.0, image.width * 72 / 96)
                height = max(72.0, image.height * 72 / 96)
            else:
                width, height = PAGE_SIZES.get(page_mode, PAGE_SIZES["a4"])

            landscape = orientation == "landscape" or (
                orientation == "auto" and image.width > image.height
            )
            if landscape and width < height or orientation == "portrait" and width > height:
                width, height = height, width

            page = document.new_page(width=width, height=height)
            area = fitz.Rect(margin, margin, width - margin, height - margin)
            if area.width <= 1 or area.height <= 1:
                raise TaskError("E1-400", "边距过大，页面没有可用区域")

            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True)
            page.insert_image(area, stream=buffer.getvalue(), keep_proportion=True)
            used_pages += 1
        except TaskError as exc:
            outcome.failures.append({"filename": name, "code": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": name, "code": "E3-422", "message": f"{name} 无法加入 PDF：{exc}"})

    if used_pages == 0:
        document.close()
        raise TaskError("E3-422", "没有可用于生成 PDF 的图片")

    filename = unique_filename(f"图片合并_{timestamp_label()}.pdf", set())
    target = workdir / filename
    document.save(str(target), garbage=3, deflate=True)
    document.close()
    outcome.results.append(
        FileResult(
            filename=filename,
            path=target,
            content_type="application/pdf",
            meta={"pages": used_pages, "images": used_pages},
        )
    )
    outcome.notes.append(f"共 {used_pages} 张图片，生成 {used_pages} 页 PDF。")
    return outcome


def process_pdf_merge(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    if len(files) < 2:
        raise TaskError("E1-400", "至少添加 2 份 PDF", 400)

    writer = PdfWriter()
    total_pages = 0
    for path, name in zip(files, names):
        reader = _pdf_writer_from(path)
        if total_pages + len(reader.pages) > MAX_TOTAL_PAGES:
            raise TaskError("E2-413", f"合并后总页数超过 {MAX_TOTAL_PAGES} 页上限", 413)
        for page in reader.pages:
            writer.add_page(page)
        total_pages += len(reader.pages)

    filename = unique_filename(f"合并_{timestamp_label()}.pdf", set())
    target = workdir / filename
    with target.open("wb") as handle:
        writer.write(handle)

    return ProcessOutcome(
        results=[
            FileResult(
                filename=filename,
                path=target,
                content_type="application/pdf",
                meta={"pages": total_pages, "files": len(files)},
            )
        ],
        notes=["原文件的数字签名已失效，书签与表单未保留。"],
    )


def process_pdf_split(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    reader = _pdf_writer_from(path)
    total = len(reader.pages)
    if total > MAX_TOTAL_PAGES:
        raise TaskError("E2-413", f"PDF 共 {total} 页，超过 {MAX_TOTAL_PAGES} 页上限", 413)

    mode = str(params.get("mode", "per_page"))
    groups: list[tuple[str, list[int]]] = []
    stem = safe_stem(name)

    if mode == "per_page":
        groups = [(f"p{index}", [index]) for index in range(1, total + 1)]
    elif mode == "every_n":
        size = int(params.get("size", 1) or 1)
        if not 1 <= size <= 100:
            raise TaskError("E1-400", "每份页数需在 1–100 之间")
        for index in range(0, total, size):
            pages = list(range(index + 1, min(index + size, total) + 1))
            groups.append((f"p{pages[0]}-{pages[-1]}", pages))
    elif mode == "range":
        expression = str(params.get("ranges", ""))
        try:
            parts = normalize_ranges(expression)
        except ValueError as exc:
            raise TaskError("E1-400", f"页码范围无法解析：{exc}；示例 1-3,5,8-10") from exc
        try:
            pages = expand_ranges(parts, total)
        except ValueError:
            raise TaskError("E2-413", f"页码范围超出有效范围 1–{total}", 413) from None
        # 重叠区间允许：合并为连续片段逐段输出
        for index, part in enumerate(parts):
            start, end = (part, part) if isinstance(part, int) else part
            label = f"p{start}" if start == end else f"p{start}-{end}"
            groups.append((label, list(range(start, end + 1))))
        if not pages:
            raise TaskError("E1-400", "页码不能为空")
    else:
        raise TaskError("E1-400", "未知的拆分模式")

    used: set[str] = set()
    results: list[FileResult] = []
    for label, pages in groups:
        writer = PdfWriter()
        for page_number in pages:
            writer.add_page(reader.pages[page_number - 1])
        filename = unique_filename(f"{stem}_{label}.pdf", used)
        target = workdir / filename
        with target.open("wb") as handle:
            writer.write(handle)
        results.append(
            FileResult(
                filename=filename,
                path=target,
                content_type="application/pdf",
                meta={"pages": len(pages), "page_range": pages[0] if len(pages) == 1 else f"{pages[0]}-{pages[-1]}"},
            )
        )

    return ProcessOutcome(
        results=results,
        notes=["拆分生成的文件不保留书签与表单，原签名已失效。"],
    )


def process_pdf_to_images(
    files: list[Path], names: list[str], params: dict, workdir: Path
) -> ProcessOutcome:
    path = files[0]
    name = names[0]
    image_format = str(params.get("format", "png")).lower()
    if image_format not in {"png", "jpg"}:
        image_format = "png"
    dpi = int(params.get("dpi", 144) or 144)
    if dpi not in {72, 144, 300}:
        dpi = 144

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        raise TaskError("E1-400", "PDF 无法读取，文件可能已损坏") from exc
    if document.needs_pass or document.is_encrypted:
        document.close()
        raise TaskError("E1-400", "PDF 已加密，请先移除打开密码")

    total = document.page_count
    if total == 0:
        document.close()
        raise TaskError("E1-400", "PDF 不含任何页面")
    if total > MAX_RENDER_PAGES and str(params.get("ranges", "")).strip() in {"", "all"}:
        document.close()
        raise TaskError("E2-413", f"PDF 共 {total} 页，单次最多转换 {MAX_RENDER_PAGES} 页，请分批处理", 413)

    expression = str(params.get("ranges", "")).strip()
    if not expression or expression == "all":
        pages = list(range(1, min(total, MAX_RENDER_PAGES) + 1))
    else:
        try:
            parts = normalize_ranges(expression)
        except ValueError as exc:
            document.close()
            raise TaskError("E1-400", f"页码范围无法解析：{exc}；示例 1-5 或 1,3,5") from exc
        try:
            pages = expand_ranges(parts, total)
        except ValueError:
            document.close()
            raise TaskError("E2-413", f"页码范围超出有效范围 1–{total}", 413) from None
        if len(pages) != len(set(pages)):
            document.close()
            raise TaskError("E1-400", "页码范围存在重叠，请合并为单个区间")
        if len(pages) > MAX_RENDER_PAGES:
            document.close()
            raise TaskError("E2-413", f"单次最多转换 {MAX_RENDER_PAGES} 页", 413)

    outcome = ProcessOutcome()
    stem = safe_stem(name)
    used: set[str] = set()
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_number in pages:
        try:
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            extension = "png" if image_format == "png" else "jpg"
            filename = unique_filename(f"{stem}_p{page_number:03d}.{extension}", used)
            target = workdir / filename
            if image_format == "png":
                pixmap.save(str(target))
            else:
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                image.convert("RGB").save(target, format="JPEG", quality=90, optimize=True)
            outcome.results.append(
                FileResult(
                    filename=filename,
                    path=target,
                    content_type="image/png" if image_format == "png" else "image/jpeg",
                    meta={"page": page_number, "dpi": dpi, "format": image_format},
                )
            )
        except Exception as exc:  # pragma: no cover
            outcome.failures.append({"filename": f"第 {page_number} 页", "code": "E3-422", "message": f"第 {page_number} 页渲染失败：{exc}"})

    document.close()
    if not outcome.results:
        raise TaskError("E3-422", "所有页面渲染失败")
    return outcome

"""工具处理引擎注册与可用性判断。"""

from pathlib import Path

from app.catalog import ToolDef
from app.services.common import tesseract_available
from app.services.images import (
    process_image_compress,
    process_image_convert,
    process_image_resize,
)
from app.services.images_extra import (
    process_icon_generator,
    process_image_stitch,
    process_image_watermark,
)
from app.services.media import (
    ffmpeg_available,
    process_audio_convert,
    process_extract_audio,
    process_speech_to_text,
    process_text_to_speech,
    process_video_compress,
    process_video_convert,
    process_video_to_gif,
    speech_available,
    tts_available,
)
from app.services.ocr import process_ocr
from app.services.ocr_extra import process_pdf_ocr, process_table_ocr
from app.services.pdfs import (
    process_images_to_pdf,
    process_pdf_merge,
    process_pdf_split,
    process_pdf_to_images,
)
from app.services.pdfs_extra import (
    office_available,
    process_office_to_pdf,
    process_pdf_compress,
    process_pdf_pages,
    process_pdf_password,
    process_pdf_to_word,
)
from app.services.types import ProcessOutcome

Processor = callable  # type: ignore[assignment]

PROCESSORS: dict[str, callable] = {
    "IMG-01": process_image_convert,
    "IMG-02": process_image_compress,
    "IMG-03": process_image_resize,
    "IMG-04": process_image_watermark,
    "IMG-05": process_image_stitch,
    "IMG-07": process_icon_generator,
    "DOC-01": process_images_to_pdf,
    "DOC-02": process_pdf_merge,
    "DOC-03": process_pdf_split,
    "DOC-04": process_pdf_to_images,
    "DOC-05": process_pdf_pages,
    "DOC-06": process_pdf_compress,
    "DOC-07": process_office_to_pdf,
    "DOC-08": process_pdf_to_word,
    "DOC-09": process_pdf_password,
    "OCR-01": process_ocr,
    "OCR-02": process_pdf_ocr,
    "OCR-03": process_table_ocr,
    "AV-01": process_audio_convert,
    "AV-02": process_video_to_gif,
    "AV-03": process_video_compress,
    "AV-04": process_extract_audio,
    "AV-05": process_video_convert,
    "AV-06": process_speech_to_text,
    "AV-07": process_text_to_speech,
}


def processor_for(code: str):
    return PROCESSORS.get(code)


def run_processor(
    code: str,
    files: list[Path],
    names: list[str],
    params: dict,
    workdir: Path,
) -> ProcessOutcome:
    processor = processor_for(code)
    if processor is None:
        raise NotImplementedError(f"{code} 暂无服务端实现")
    return processor(files, names, params, workdir)


def availability(tool: ToolDef) -> tuple[bool, str | None]:
    if not tool.implemented:
        return False, "该工具尚未实现"
    if tool.code in {"OCR-01", "OCR-02", "OCR-03"} and not tesseract_available():
        return False, "服务端 OCR 引擎暂不可用，请联系维护者"
    if tool.code == "DOC-07" and not office_available():
        return False, "Office 转换引擎不可用，请联系维护者"
    if tool.code.startswith("AV-") and tool.code not in {"AV-06", "AV-07"} and not ffmpeg_available():
        return False, "音视频转码引擎不可用，请联系维护者"
    if tool.code == "AV-06" and not speech_available():
        return False, "语音识别引擎不可用，请联系维护者"
    if tool.code == "AV-07" and not tts_available():
        return False, "语音合成引擎不可用，请联系维护者"
    return True, None

"""OCR：使用本机 Tesseract 引擎；引擎缺失时明确返回不可用，不伪造结果。"""

from pathlib import Path

import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

from app.services.common import safe_stem, tesseract_available
from app.services.types import ProcessOutcome, TaskError, TextResult

LANGUAGE_MAP = {
    "mixed": "chi_sim+eng",
    "zh-CN": "chi_sim",
    "zh-TW": "chi_tra",
    "en": "eng",
}


def _auto_rotate(image: Image.Image) -> Image.Image:
    try:
        osd = pytesseract.image_to_osd(image, output_type=Output.DICT)
        angle = int(osd.get("rotate", 0) or 0)
    except Exception:
        return image
    if angle:
        return image.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
    return image


def process_ocr(files: list[Path], names: list[str], params: dict, workdir: Path) -> ProcessOutcome:
    if not tesseract_available():
        raise TaskError(
            "E4-503",
            "服务端 OCR 引擎暂不可用，请联系维护者；其他工具不受影响。",
            503,
        )

    language = LANGUAGE_MAP.get(str(params.get("language", "mixed")), "chi_sim+eng")
    auto_rotate = bool(params.get("auto_rotate", True))
    outcome = ProcessOutcome()

    for path, name in zip(files, names):
        try:
            image = Image.open(path)
            image.seek(0)
            image.load()
            image = ImageOps.exif_transpose(image)
            if max(image.size) > 10000:
                outcome.failures.append(
                    {
                        "filename": name,
                        "code": "E2-413",
                        "message": "单边超过 10000px 上限，请先缩小图片。",
                    }
                )
                continue
            if auto_rotate:
                image = _auto_rotate(image)

            text = pytesseract.image_to_string(image, lang=language, timeout=60).strip()
            if not text:
                outcome.failures.append(
                    {
                        "filename": name,
                        "code": "E3-422",
                        "message": "未识别到文字，可能是纯图、低对比或语言不匹配。",
                    }
                )
                continue

            stem = safe_stem(name)
            outcome.results.append(
                TextResult(
                    filename=f"{stem}.txt",
                    text=text,
                    meta={
                        "source": name,
                        "language": language,
                        "chars": len(text),
                        "engine": "tesseract",
                    },
                )
            )
        except pytesseract.TesseractNotFoundError:
            raise TaskError("E4-503", "服务端 OCR 引擎暂不可用，请联系维护者", 503) from None
        except RuntimeError as exc:
            outcome.failures.append(
                {"filename": name, "code": "E4-504", "message": f"识别超时或失败：{exc}"}
            )
        except Exception as exc:  # pragma: no cover
            outcome.failures.append(
                {"filename": name, "code": "E3-422", "message": f"{name} 识别失败：{exc}"}
            )

    if outcome.results:
        outcome.notes.append("识别结果需人工校对。")
    return outcome

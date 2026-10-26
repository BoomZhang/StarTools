"""产品枚举与共享校验规则。"""

from app.catalog import ToolDef

FEEDBACK_TYPES: dict[str, str] = {
    "bug": "功能异常",
    "wrong_result": "结果不正确",
    "page": "页面或操作异常",
    "copy": "文案或内容错误",
    "tool_request": "希望增加其他工具",
    "other": "其他",
}

FEEDBACK_STATUSES: dict[str, str] = {
    "pending": "待处理",
    "processing": "处理中",
    "resolved": "已解决",
    "ignored": "已忽略",
}

ALLOWED_FEEDBACK_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"processing", "ignored"},
    "processing": {"resolved", "ignored"},
    "resolved": {"processing"},
    "ignored": {"processing"},
}

USAGE_RESULTS = {"succeeded", "partial", "failed", "canceled"}

SINGLE_FILE_CODES = {
    "IMG-06", "IMG-07", "TXT-01",
    "DOC-03", "DOC-04", "DOC-05", "DOC-06", "DOC-07", "DOC-08", "DOC-09",
    "ENC-01", "ENC-03",
    "QR-02", "QR-03", "QR-04",
    "OCR-02",
    "AV-01", "AV-02", "AV-03", "AV-04", "AV-05", "AV-06", "AV-07",
}

CATEGORY_HARD_LIMIT_MB = {
    "image": 200,
    "document": 500,
    "text": 200,
    "encoding": 200,
    "qr": 50,
    "ocr": 50,
    "av": 500,
}

VIDEO_CODES = {"AV-02", "AV-03", "AV-04", "AV-05"}


def hard_file_limit_mb(tool: ToolDef) -> int:
    if tool.code in VIDEO_CODES:
        return 2048
    return CATEGORY_HARD_LIMIT_MB.get(tool.category, 200)


def max_count_limit(tool: ToolDef) -> int:
    return 1 if tool.code in SINGLE_FILE_CODES else 50

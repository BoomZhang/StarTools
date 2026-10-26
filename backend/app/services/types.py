from dataclasses import dataclass, field
from pathlib import Path


class TaskError(Exception):
    """可直接展示给访客的处理错误，错误号遵循 R-08。"""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass
class FileResult:
    filename: str
    path: Path
    content_type: str = "application/octet-stream"
    meta: dict = field(default_factory=dict)


@dataclass
class TextResult:
    filename: str
    text: str
    meta: dict = field(default_factory=dict)


@dataclass
class ProcessOutcome:
    results: list[FileResult | TextResult] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.results and self.failures:
            return "partial"
        if self.results:
            return "succeeded"
        return "failed"

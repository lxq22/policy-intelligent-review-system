from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class UnsupportedDocumentError(ValueError):
    """Raised when a document type is outside the M4 parsing scope."""


class DocumentParseError(ValueError):
    """Raised when a supported document cannot be read."""


class ScannedPdfError(DocumentParseError):
    """Raised when a PDF has no selectable text and would require OCR."""


@dataclass(frozen=True)
class ExtractedParagraph:
    sequence: int
    text: str


class DocumentParser(Protocol):
    def extract(self, path: Path) -> list[ExtractedParagraph]: ...

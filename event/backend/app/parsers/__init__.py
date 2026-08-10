from pathlib import Path

from .base import (
    DocumentParseError,
    DocumentParser,
    ExtractedParagraph,
    ScannedPdfError,
    UnsupportedDocumentError,
)
from .docx_parser import DocxParser
from .pdf_parser import PdfTextParser


def parser_for(path: Path) -> DocumentParser:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return DocxParser()
    if suffix == ".pdf":
        return PdfTextParser()
    raise UnsupportedDocumentError("仅支持 DOCX 和带可选文字的 PDF 文件")


__all__ = [
    "DocumentParseError",
    "ExtractedParagraph",
    "ScannedPdfError",
    "UnsupportedDocumentError",
    "parser_for",
]

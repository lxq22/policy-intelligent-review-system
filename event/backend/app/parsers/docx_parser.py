from pathlib import Path

from docx import Document

from .base import DocumentParseError, ExtractedParagraph


class DocxParser:
    def extract(self, path: Path) -> list[ExtractedParagraph]:
        try:
            document = Document(path)
            return [
                ExtractedParagraph(sequence=index, text=paragraph.text.strip())
                for index, paragraph in enumerate(document.paragraphs, start=1)
                if paragraph.text.strip()
            ]
        except Exception as exc:
            raise DocumentParseError("无法解析 DOCX 文件") from exc

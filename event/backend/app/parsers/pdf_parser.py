from pathlib import Path

import fitz

from .base import DocumentParseError, ExtractedParagraph, ScannedPdfError


class PdfTextParser:
    def extract(self, path: Path) -> list[ExtractedParagraph]:
        paragraphs: list[ExtractedParagraph] = []
        try:
            with fitz.open(path) as document:
                sequence = 1
                for page in document:
                    blocks = sorted(
                        page.get_text("blocks"),
                        key=lambda block: (round(block[1], 1), round(block[0], 1)),
                    )
                    for block in blocks:
                        text = " ".join(block[4].split()).strip()
                        if text:
                            paragraphs.append(
                                ExtractedParagraph(sequence=sequence, text=text)
                            )
                            sequence += 1
        except Exception as exc:
            raise DocumentParseError("无法解析 PDF 文件") from exc

        if not paragraphs:
            raise ScannedPdfError(
                "PDF 未检测到可选文字，疑似扫描文件；当前版本不支持 OCR"
            )
        return paragraphs

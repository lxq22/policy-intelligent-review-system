from __future__ import annotations

import re
from dataclasses import dataclass

from .base import ExtractedParagraph


_NUMBER = r"[一二三四五六七八九十百千零〇两\d]+"
_CHAPTER = re.compile(rf"^(第{_NUMBER}章)\s*(.*)$")
_SECTION = re.compile(rf"^(第{_NUMBER}节)\s*(.*)$")
_ARTICLE = re.compile(rf"^(第{_NUMBER}条)\s*(.*)$")


@dataclass
class ParsedClause:
    original_no: str
    title: str
    content: str
    level: str
    heading_path: list[str]
    paragraph_start: int
    paragraph_end: int
    sequence: int


class ClauseSegmenter:
    def segment(self, paragraphs: list[ExtractedParagraph]) -> list[ParsedClause]:
        clauses: list[ParsedClause] = []
        current_chapter: str | None = None
        current_section: str | None = None
        current: ParsedClause | None = None

        for paragraph in paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            chapter = _CHAPTER.match(text)
            if chapter:
                current_chapter = self._heading_text(chapter)
                current_section = None
                current = None
                continue

            section = _SECTION.match(text)
            if section:
                current_section = self._heading_text(section)
                current = None
                continue

            article = _ARTICLE.match(text)
            if article:
                heading_path = [
                    heading
                    for heading in (current_chapter, current_section)
                    if heading is not None
                ]
                current = ParsedClause(
                    original_no=article.group(1),
                    title="",
                    content=article.group(2).strip(),
                    level="article",
                    heading_path=heading_path,
                    paragraph_start=paragraph.sequence,
                    paragraph_end=paragraph.sequence,
                    sequence=len(clauses) + 1,
                )
                clauses.append(current)
                continue

            if current is not None:
                current.content = "\n".join(
                    part for part in (current.content, text) if part
                )
                current.paragraph_end = paragraph.sequence

        return clauses

    @staticmethod
    def _heading_text(match: re.Match[str]) -> str:
        return " ".join(part for part in match.groups() if part).strip()

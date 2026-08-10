from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import Clause, Regulation, RegulationVersion, TemporaryReviewFile
from ..parsers import DocumentParseError, parser_for
from ..parsers.segmenter import ClauseSegmenter, ParsedClause
from ..retrieval.embeddings import DeterministicEmbeddingProvider
from .file_storage import FileStorage


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ParseService:
    def __init__(self, storage_root: str | Path):
        self.storage = FileStorage(storage_root)
        self.embedding_provider = DeterministicEmbeddingProvider()

    def parse_version(self, db: Session, version_id: int) -> list[Clause]:
        owner = db.get(RegulationVersion, version_id)
        if owner is None:
            raise ValueError("制度版本不存在")
        regulation = db.get(Regulation, owner.regulation_id)
        return self._parse(db, owner, regulation_version_id=owner.id, regulation=regulation)

    def parse_temporary_file(self, db: Session, temporary_file_id: int) -> list[Clause]:
        owner = db.get(TemporaryReviewFile, temporary_file_id)
        if owner is None:
            raise ValueError("临时待审文件不存在")
        return self._parse(db, owner, temporary_file_id=owner.id)

    def _parse(
        self,
        db: Session,
        owner: RegulationVersion | TemporaryReviewFile,
        *,
        regulation_version_id: int | None = None,
        temporary_file_id: int | None = None,
        regulation: Regulation | None = None,
    ) -> list[Clause]:
        source_filter = (
            Clause.regulation_version_id == regulation_version_id
            if regulation_version_id is not None
            else Clause.temporary_file_id == temporary_file_id
        )
        had_previous = bool(db.scalar(select(func.count(Clause.id)).where(source_filter)))
        owner.parse_status = "解析中"
        owner.parse_error = None
        if regulation is not None:
            regulation.parse_status = "解析中"
        db.commit()

        try:
            if not owner.stored_path:
                raise DocumentParseError("无法解析：未找到已保存的源文件")
            path = self.storage.resolve(owner.stored_path)
            paragraphs = parser_for(path).extract(path)
            parsed = ClauseSegmenter().segment(paragraphs)
            if not parsed:
                raise DocumentParseError("无法解析：文件中未识别到条款")
            rows = self._clause_rows(parsed, regulation_version_id, temporary_file_id)

            db.execute(delete(Clause).where(source_filter))
            db.add_all(rows)
            owner.parse_status = "解析成功"
            owner.parse_error = None
            owner.parsed_at = _now()
            if regulation is not None:
                regulation.parse_status = "解析成功"
            db.commit()
            for row in rows:
                db.refresh(row)
            return rows
        except Exception as exc:
            db.rollback()
            owner = db.get(type(owner), owner.id)
            message = str(exc) or "无法解析文件"
            owner.parse_status = "解析成功" if had_previous else "解析失败"
            owner.parse_error = message
            if regulation is not None:
                regulation = db.get(Regulation, regulation.id)
                regulation.parse_status = owner.parse_status
            db.commit()
            raise

    def _clause_rows(
        self,
        parsed: list[ParsedClause],
        regulation_version_id: int | None,
        temporary_file_id: int | None,
    ) -> list[Clause]:
        return [
            Clause(
                regulation_version_id=regulation_version_id,
                temporary_file_id=temporary_file_id,
                sequence=item.sequence,
                original_no=item.original_no,
                title=item.title,
                content=item.content,
                level=item.level,
                heading_path=item.heading_path,
                paragraph_start=item.paragraph_start,
                paragraph_end=item.paragraph_end,
                embedding=self.embedding_provider.embed(item.content),
            )
            for item in parsed
        ]

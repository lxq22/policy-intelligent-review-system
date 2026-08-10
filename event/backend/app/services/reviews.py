from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import (
    Clause,
    Regulation,
    RegulationVersion,
    ReviewRecord,
    TemporaryReviewFile,
    User,
)
from ..schemas import ReviewCreate
from .candidates import CandidateService


class ReviewService:
    def create(self, db: Session, user: User, payload: ReviewCreate) -> ReviewRecord:
        source_name, source_rows = self._source_snapshot(db, payload)
        candidate_rows = self._candidate_snapshot(db, payload)
        now = datetime.now(UTC).replace(tzinfo=None)

        for _ in range(5):
            record = ReviewRecord(
                record_code=self._next_code(db, source_name, now),
                source_type=payload.source_type,
                regulation_id=payload.regulation_id,
                temporary_file_id=payload.temporary_file_id,
                regulation_name=source_name,
                dimensions=list(payload.dimensions),
                source_snapshot=source_rows,
                candidate_snapshot=candidate_rows,
                created_by=user.id,
                created_at=now,
                completed_at=now,
            )
            db.add(record)
            try:
                db.commit()
                db.refresh(record)
                return record
            except IntegrityError:
                db.rollback()
        raise RuntimeError("审查记录编号生成失败，请重试")

    def _source_snapshot(
        self, db: Session, payload: ReviewCreate
    ) -> tuple[str, list[dict]]:
        if payload.source_type == "regulation":
            if payload.regulation_id is None:
                raise ValueError("正式制度审查必须指定待审制度")
            regulation = db.get(Regulation, payload.regulation_id)
            if regulation is None or regulation.deleted_at is not None:
                raise ValueError("待审制度不存在")
            clauses = list(
                db.execute(
                    select(Clause, RegulationVersion)
                    .join(
                        RegulationVersion,
                        Clause.regulation_version_id == RegulationVersion.id,
                    )
                    .where(
                        Clause.id.in_(payload.clause_ids),
                        RegulationVersion.regulation_id == regulation.id,
                    )
                )
            )
            if {clause.id for clause, _ in clauses} != set(payload.clause_ids):
                raise ValueError("所选条款不属于当前待审制度")
            by_id = {clause.id: (clause, version) for clause, version in clauses}
            snapshots = [
                self._snapshot_clause(
                    by_id[clause_id][0],
                    regulation.id,
                    regulation.name or "未命名制度",
                    by_id[clause_id][1].version,
                )
                for clause_id in payload.clause_ids
            ]
            return regulation.name or "未命名制度", snapshots

        if payload.temporary_file_id is None:
            raise ValueError("临时文件审查必须指定待审文件")
        temporary = db.get(TemporaryReviewFile, payload.temporary_file_id)
        if temporary is None:
            raise ValueError("临时待审文件不存在")
        clauses = list(
            db.scalars(
                select(Clause).where(
                    Clause.id.in_(payload.clause_ids),
                    Clause.temporary_file_id == temporary.id,
                )
            )
        )
        if {item.id for item in clauses} != set(payload.clause_ids):
            raise ValueError("所选条款不属于当前临时待审文件")
        by_id = {item.id: item for item in clauses}
        source_name = Path(temporary.original_name).stem
        snapshots = [
            self._snapshot_clause(by_id[clause_id], None, source_name, None)
            for clause_id in payload.clause_ids
        ]
        return source_name, snapshots

    @staticmethod
    def _snapshot_clause(
        clause: Clause,
        regulation_id: int | None,
        regulation_name: str,
        version: str | None,
    ) -> dict:
        location = " > ".join([*clause.heading_path, clause.original_no])
        return {
            "clause_id": clause.id,
            "regulation_id": regulation_id,
            "regulation_name": regulation_name,
            "version": version,
            "original_no": clause.original_no,
            "location": location,
            "text": clause.content,
        }

    def _candidate_snapshot(self, db: Session, payload: ReviewCreate) -> list[dict]:
        if "conflict" not in payload.dimensions:
            return []
        if not payload.candidate_clause_ids:
            raise ValueError("制度冲突审查必须选择候选对比条款")
        service = CandidateService()
        if payload.source_type == "regulation":
            available = service.for_regulation(
                db, payload.regulation_id or 0, payload.clause_ids
            )
        else:
            available = service.for_temporary(
                db,
                payload.temporary_file_id or 0,
                payload.clause_ids,
                payload.comparison_regulation_ids,
            )
        by_id = {item.clause_id: item for item in available}
        if not set(payload.candidate_clause_ids).issubset(by_id):
            raise ValueError("所选候选条款超出允许的制度关系范围")
        return [
            {
                "clause_id": item.clause_id,
                "regulation_id": item.regulation_id,
                "regulation_name": item.regulation_name,
                "version": item.version,
                "original_no": item.original_no,
                "location": " > ".join([*item.heading_path, item.original_no]),
                "text": item.content,
                "retrieval_evidence": item.evidence,
            }
            for item in (by_id[clause_id] for clause_id in payload.candidate_clause_ids)
        ]

    @staticmethod
    def _next_code(db: Session, source_name: str, now: datetime) -> str:
        prefix = f"{source_name}-{now:%Y%m%d}-"
        existing = list(
            db.scalars(
                select(ReviewRecord.record_code).where(
                    ReviewRecord.record_code.like(f"{prefix}%")
                )
            )
        )
        numbers = [
            int(code.rsplit("-", 1)[-1])
            for code in existing
            if code.rsplit("-", 1)[-1].isdigit()
        ]
        return f"{prefix}{max(numbers, default=0) + 1:02d}"

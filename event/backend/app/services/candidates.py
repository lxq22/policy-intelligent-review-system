from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Clause, Regulation, RegulationVersion, TemporaryReviewFile
from ..retrieval.embeddings import DeterministicEmbeddingProvider
from ..retrieval.ranking import rrf
from ..retrieval.tokenizer import tokenize
from .relations import collect_relations


@dataclass(frozen=True)
class CandidateClause:
    clause_id: int
    regulation_id: int
    regulation_name: str
    version: str | None
    original_no: str
    content: str
    heading_path: list[str]
    score: float
    evidence: list[str]


class CandidateService:
    def __init__(self):
        self.embedding_provider = DeterministicEmbeddingProvider()
        self.settings = get_settings()

    def for_regulation(
        self, db: Session, regulation_id: int, clause_ids: list[int]
    ) -> list[CandidateClause]:
        regulation = db.get(Regulation, regulation_id)
        if regulation is None or regulation.deleted_at is not None:
            raise ValueError("待审制度不存在")
        sources = self._regulation_source_clauses(db, regulation_id, clause_ids)
        relation_ids = {item.target_id for item in collect_relations(db, regulation)}
        candidates = self._candidate_rows(db, relation_ids)
        return self._rank(sources, candidates)

    def for_temporary(
        self,
        db: Session,
        temporary_file_id: int,
        clause_ids: list[int],
        comparison_regulation_ids: list[int],
    ) -> list[CandidateClause]:
        temporary = db.get(TemporaryReviewFile, temporary_file_id)
        if temporary is None or temporary.parse_status != "解析成功":
            raise ValueError("临时待审文件不存在或尚未解析成功")
        sources = list(
            db.scalars(
                select(Clause).where(
                    Clause.id.in_(clause_ids),
                    Clause.temporary_file_id == temporary_file_id,
                )
            )
        )
        self._assert_ownership(sources, clause_ids)
        candidates = self._candidate_rows(db, set(comparison_regulation_ids))
        return self._rank(sources, candidates)

    def _regulation_source_clauses(
        self, db: Session, regulation_id: int, clause_ids: list[int]
    ) -> list[Clause]:
        sources = list(
            db.scalars(
                select(Clause)
                .join(
                    RegulationVersion,
                    Clause.regulation_version_id == RegulationVersion.id,
                )
                .where(
                    Clause.id.in_(clause_ids),
                    RegulationVersion.regulation_id == regulation_id,
                )
            )
        )
        self._assert_ownership(sources, clause_ids)
        return sources

    @staticmethod
    def _assert_ownership(sources: list[Clause], clause_ids: list[int]) -> None:
        if not clause_ids or {item.id for item in sources} != set(clause_ids):
            raise ValueError("所选条款不属于当前待审制度")

    @staticmethod
    def _candidate_rows(
        db: Session, regulation_ids: set[int]
    ) -> list[tuple[Clause, Regulation, RegulationVersion]]:
        if not regulation_ids:
            return []
        active = list(
            db.scalars(
                select(Regulation).where(
                    Regulation.id.in_(regulation_ids),
                    Regulation.deleted_at.is_(None),
                    Regulation.parse_status == "解析成功",
                )
            )
        )
        rows: list[tuple[Clause, Regulation, RegulationVersion]] = []
        for regulation in active:
            version = db.scalar(
                select(RegulationVersion)
                .where(
                    RegulationVersion.regulation_id == regulation.id,
                    RegulationVersion.parse_status == "解析成功",
                )
                .order_by(RegulationVersion.id.desc())
                .limit(1)
            )
            if version is None:
                continue
            for clause in db.scalars(
                select(Clause)
                .where(Clause.regulation_version_id == version.id)
                .order_by(Clause.sequence)
            ):
                rows.append((clause, regulation, version))
        return rows

    def _rank(
        self,
        sources: list[Clause],
        candidates: list[tuple[Clause, Regulation, RegulationVersion]],
    ) -> list[CandidateClause]:
        query_text = "\n".join(item.content for item in sources)
        query_tokens = set(tokenize(query_text))
        query_vector = self.embedding_provider.embed(query_text)
        keyword_ids = [
            item[0].id
            for item in sorted(
                candidates,
                key=lambda row: (
                    -len(query_tokens.intersection(tokenize(row[0].content))),
                    row[0].id,
                ),
            )
        ]
        vector_ids = [
            item[0].id
            for item in sorted(
                candidates,
                key=lambda row: (-self._cosine(query_vector, row[0].embedding), row[0].id),
            )
        ]
        metadata = {row[0].id: row for row in candidates}
        results: list[CandidateClause] = []
        for clause_id, score, evidence in rrf(
            keyword_ids, vector_ids, k=self.settings.rrf_k
        )[: self.settings.retrieval_top_k]:
            clause, regulation, version = metadata[clause_id]
            results.append(
                CandidateClause(
                    clause_id=clause.id,
                    regulation_id=regulation.id,
                    regulation_name=regulation.name or "未命名制度",
                    version=version.version,
                    original_no=clause.original_no,
                    content=clause.content,
                    heading_path=clause.heading_path,
                    score=score,
                    evidence=evidence,
                )
            )
        return results

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right)) / (
            (math.sqrt(sum(a * a for a in left)) or 1.0)
            * (math.sqrt(sum(b * b for b in right)) or 1.0)
        )

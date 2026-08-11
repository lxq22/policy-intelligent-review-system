from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from threading import Lock

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import ReviewIssue, ReviewRecord
from ..providers.chat import ChatModelProvider, ChatProviderResponseError
from ..reviewing.local_rules import review_locally
from ..reviewing.prompts import build_messages
from ..reviewing.schemas import DimensionResult, IssueDraft

ProgressCallback = Callable[[str, str], None]
_execution_locks_guard = Lock()
_execution_locks: dict[int, Lock] = {}


def _single_execution_per_record(method):
    @wraps(method)
    def synchronized(self, db, review_id, *args, **kwargs):
        with _execution_locks_guard:
            lock = _execution_locks.setdefault(review_id, Lock())
        with lock:
            return method(self, db, review_id, *args, **kwargs)

    return synchronized


class ReviewExecutionError(RuntimeError):
    pass


class ReviewExecutionService:
    @_single_execution_per_record
    def execute(
        self,
        db: Session,
        review_id: int,
        provider: ChatModelProvider,
        on_progress: ProgressCallback | None = None,
    ) -> list[ReviewIssue]:
        record = db.scalar(
            select(ReviewRecord)
            .options(selectinload(ReviewRecord.issues))
            .where(ReviewRecord.id == review_id)
            .with_for_update()
        )
        if record is None:
            raise ReviewExecutionError("审查记录不存在")
        if record.completed_at is not None:
            return list(record.issues)

        source_by_id = {item["clause_id"]: item for item in record.source_snapshot}
        candidate_by_id = {
            item["clause_id"]: item for item in record.candidate_snapshot
        }
        prepared: list[tuple[str, IssueDraft]] = []

        try:
            for dimension in record.dimensions:
                if on_progress:
                    on_progress("dimension", dimension)
                local = review_locally(dimension, record.source_snapshot)
                model = self._review_dimension(
                    provider,
                    dimension,
                    record.source_snapshot,
                    record.candidate_snapshot,
                    local,
                    source_by_id,
                    candidate_by_id,
                )
                prepared.extend((dimension, item) for item in local)
                prepared.extend((dimension, item) for item in model)

            prepared = self._deduplicate(prepared)
            if on_progress:
                on_progress("saving", "正在保存审查报告")
            issues = [
                self._to_model(record.id, dimension, draft, source_by_id, candidate_by_id)
                for dimension, draft in prepared
            ]
            db.add_all(issues)
            record.completed_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            for issue in issues:
                db.refresh(issue)
            return issues
        except Exception:
            db.rollback()
            raise

    def _review_dimension(
        self,
        provider: ChatModelProvider,
        dimension: str,
        sources: list[dict],
        candidates: list[dict],
        local: list[IssueDraft],
        source_by_id: dict[int, dict],
        candidate_by_id: dict[int, dict],
    ) -> list[IssueDraft]:
        messages = build_messages(
            dimension,
            sources,
            candidates,
            [item.model_dump() for item in local],
        )
        last_error: Exception | None = None
        for attempt in range(2):
            attempt_messages = list(messages)
            if attempt:
                attempt_messages.append(
                    {
                        "role": "user",
                        "content": "上一次输出不符合格式或引用了不存在的条款。请修正，只使用输入中的条款 ID，并返回完整 JSON。",
                    }
                )
            try:
                raw = provider.complete(
                    attempt_messages, response_format={"type": "json_object"}
                )
                result = DimensionResult.model_validate(raw)
                self._validate_evidence(
                    dimension, result.issues, source_by_id, candidate_by_id
                )
                return result.issues
            except (ValidationError, ChatProviderResponseError, ReviewExecutionError) as exc:
                last_error = exc
        raise ReviewExecutionError("模型连续两次返回了无法使用的审查结果") from last_error

    @staticmethod
    def _validate_evidence(
        dimension: str,
        drafts: list[IssueDraft],
        source_by_id: dict[int, dict],
        candidate_by_id: dict[int, dict],
    ) -> None:
        for draft in drafts:
            if draft.source_clause_id not in source_by_id:
                raise ReviewExecutionError("模型引用了不存在的待审条款")
            allowed = candidate_by_id if dimension == "conflict" else source_by_id
            if any(item not in allowed for item in draft.evidence_clause_ids):
                raise ReviewExecutionError("模型引用了不存在的证据条款")
            if (
                dimension == "conflict"
                and not draft.insufficient_evidence
                and not draft.evidence_clause_ids
            ):
                raise ReviewExecutionError("冲突问题缺少对比证据条款")

    @staticmethod
    def _to_model(
        review_id: int,
        dimension: str,
        draft: IssueDraft,
        source_by_id: dict[int, dict],
        candidate_by_id: dict[int, dict],
    ) -> ReviewIssue:
        source = source_by_id[draft.source_clause_id]
        details = dict(draft.details)
        if dimension == "conflict" and draft.evidence_clause_ids:
            evidence_items = [candidate_by_id[item] for item in draft.evidence_clause_ids]
            evidence = evidence_items[0]
            details.update(
                {
                    "comparison_clause_id": evidence["clause_id"],
                    "comparison_regulation_name": evidence["regulation_name"],
                    "comparison_original": evidence["text"],
                    "comparison_location": evidence["location"],
                    "comparison_evidence": [
                        {
                            "clause_id": item["clause_id"],
                            "regulation_name": item["regulation_name"],
                            "original": item["text"],
                            "location": item["location"],
                        }
                        for item in evidence_items
                    ],
                }
            )
        elif draft.evidence_clause_ids:
            details["related_evidence"] = [
                {
                    "clause_id": source_by_id[item]["clause_id"],
                    "original": source_by_id[item]["text"],
                    "location": source_by_id[item]["location"],
                }
                for item in draft.evidence_clause_ids
            ]
        return ReviewIssue(
            review_record_id=review_id,
            dimension=dimension,
            original=source["text"],
            location=source["location"],
            explanation=draft.explanation,
            consequence=draft.consequence,
            suggestion=draft.suggestion,
            insufficient_evidence=draft.insufficient_evidence,
            details=details,
        )

    @staticmethod
    def _deduplicate(
        items: list[tuple[str, IssueDraft]],
    ) -> list[tuple[str, IssueDraft]]:
        result: list[tuple[str, IssueDraft]] = []
        seen: set[tuple] = set()
        for dimension, item in items:
            marker = (
                dimension,
                item.source_clause_id,
                item.details.get("ambiguous_expression"),
                item.details.get("rule_category"),
                item.explanation,
            )
            if marker not in seen:
                seen.add(marker)
                result.append((dimension, item))
        return result

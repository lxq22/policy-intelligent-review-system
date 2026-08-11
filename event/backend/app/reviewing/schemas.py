from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IssueDraft(BaseModel):
    source_clause_id: int
    explanation: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    insufficient_evidence: bool = False
    evidence_clause_ids: list[int] = []
    details: dict[str, Any] = {}

    model_config = ConfigDict(extra="forbid")


class DimensionResult(BaseModel):
    issues: list[IssueDraft]

    model_config = ConfigDict(extra="forbid")

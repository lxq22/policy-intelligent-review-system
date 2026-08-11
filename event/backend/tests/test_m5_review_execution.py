import pytest
from sqlalchemy import select

from app.models import ReviewIssue, ReviewRecord


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, messages, response_format=None):
        self.calls.append({"messages": messages, "response_format": response_format})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_record(db, dimensions):
    record = ReviewRecord(
        record_code="M5-测试-01",
        regulation_name="待审制度",
        dimensions=dimensions,
        source_snapshot=[
            {
                "clause_id": 11,
                "regulation_id": 1,
                "regulation_name": "待审制度",
                "version": "V1.0",
                "original_no": "第三条",
                "location": "第一章 > 第三条",
                "text": "业务部门应及时完成复核。",
            }
        ],
        candidate_snapshot=[
            {
                "clause_id": 21,
                "regulation_id": 2,
                "regulation_name": "上位制度",
                "version": "V2.0",
                "original_no": "第五条",
                "location": "第二章 > 第五条",
                "text": "业务部门应在两个工作日内完成复核。",
                "retrieval_evidence": ["同部门制度"],
            }
        ],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_local_rules_find_ambiguous_terms_and_numbering_gaps():
    from app.reviewing.local_rules import review_locally

    snapshots = [
        {"clause_id": 1, "original_no": "第一条", "location": "第一条", "text": "应及时处理。"},
        {"clause_id": 2, "original_no": "第三条", "location": "第三条", "text": "材料如下。。"},
    ]

    semantic = review_locally("semantic", snapshots)
    rule = review_locally("rule", snapshots)

    assert semantic[0].source_clause_id == 1
    assert semantic[0].details["ambiguous_expression"] == "及时"
    assert any(item.details.get("rule_category") == "条款编号" for item in rule)
    assert any(item.details.get("rule_category") == "行文规范" for item in rule)


def test_execution_combines_local_and_glm_results_with_trusted_evidence(db):
    from app.services.review_execution import ReviewExecutionService

    record = make_record(db, ["semantic", "conflict"])
    provider = FakeProvider(
        [
            {
                "issues": [
                    {
                        "source_clause_id": 11,
                        "explanation": "职责主体可能不明确。",
                        "consequence": "不同部门可能相互推诿。",
                        "suggestion": "明确具体业务部门名称。",
                        "insufficient_evidence": True,
                        "evidence_clause_ids": [],
                        "details": {"ambiguous_expression": "业务部门"},
                    }
                ]
            },
            {
                "issues": [
                    {
                        "source_clause_id": 11,
                        "explanation": "处理期限与上位制度不一致。",
                        "consequence": "可能违反上位制度要求。",
                        "suggestion": "修改为两个工作日内。",
                        "insufficient_evidence": False,
                        "evidence_clause_ids": [21],
                        "details": {"conflict_type": "期限冲突"},
                    }
                ]
            },
        ]
    )

    issues = ReviewExecutionService().execute(db, record.id, provider)

    assert len(provider.calls) == 2
    assert provider.calls[0]["response_format"] == {"type": "json_object"}
    assert len(issues) == 3  # 1 条本地明确问题 + 2 条 GLM 语义问题
    conflict = next(item for item in issues if item.dimension == "conflict")
    assert conflict.original == "业务部门应及时完成复核。"
    assert conflict.location == "第一章 > 第三条"
    assert conflict.details["comparison_original"] == "业务部门应在两个工作日内完成复核。"
    assert conflict.details["comparison_location"] == "第二章 > 第五条"
    assert db.get(ReviewRecord, record.id).completed_at is not None


def test_invalid_model_evidence_is_retried_once(db):
    from app.services.review_execution import ReviewExecutionService

    record = make_record(db, ["semantic"])
    provider = FakeProvider(
        [
            {"issues": [{"source_clause_id": 999, "explanation": "伪造位置"}]},
            {"issues": []},
        ]
    )

    issues = ReviewExecutionService().execute(db, record.id, provider)

    assert len(provider.calls) == 2
    assert "修正" in provider.calls[1]["messages"][-1]["content"]
    assert len(issues) == 1  # 本地规则识别“及时”


def test_failed_dimension_rolls_back_all_partial_results(db):
    from app.services.review_execution import ReviewExecutionError, ReviewExecutionService

    record = make_record(db, ["semantic", "rule"])
    valid = {"issues": []}
    invalid = {"issues": [{"source_clause_id": 999, "explanation": "伪造位置"}]}
    provider = FakeProvider([valid, invalid, invalid])

    with pytest.raises(ReviewExecutionError):
        ReviewExecutionService().execute(db, record.id, provider)

    assert list(db.scalars(select(ReviewIssue).where(ReviewIssue.review_record_id == record.id))) == []
    db.refresh(record)
    assert record.completed_at is None

import time

from app.main import app
from app.models import ReviewIssue, ReviewRecord, User
from app.providers.chat import get_chat_provider


class FakeProvider:
    def complete(self, messages, response_format=None):
        return {"issues": []}


class SlowProvider:
    def complete(self, messages, response_format=None):
        time.sleep(0.05)
        return {"issues": []}


def create_record(db, code="API-M5-01", text="应及时处理。"):
    user = db.query(User).filter(User.username == "reviewer").one()
    record = ReviewRecord(
        record_code=code,
        regulation_name="接口测试制度",
        dimensions=["semantic"],
        source_snapshot=[
            {
                "clause_id": 101,
                "regulation_id": 1,
                "regulation_name": "接口测试制度",
                "version": "V1.0",
                "original_no": "第一条",
                "location": "第一条",
                "text": text,
            }
        ],
        candidate_snapshot=[],
        created_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


def test_execute_stream_creates_report_and_detail_counts_problems(reviewer_client):
    from app.database import SessionLocal

    with SessionLocal() as db:
        review_id = create_record(db)
    app.dependency_overrides[get_chat_provider] = lambda: FakeProvider()
    try:
        response = reviewer_client.post(f"/api/v1/reviews/{review_id}/execute")
    finally:
        app.dependency_overrides.pop(get_chat_provider, None)

    assert response.status_code == 200
    assert "event: started" in response.text
    assert "event: dimension" in response.text
    assert "event: completed" in response.text

    detail = reviewer_client.get(f"/api/v1/reviews/{review_id}")
    issues = reviewer_client.get(f"/api/v1/reviews/{review_id}/issues")
    assert detail.json()["created_by_name"] == "李明"
    assert detail.json()["problem_count"] == 1
    assert detail.json()["has_report"] is True
    assert issues.status_code == 200
    assert issues.json()[0]["original"] == "应及时处理。"


def test_execute_stream_sends_heartbeat_while_model_is_slow(
    reviewer_client, monkeypatch
):
    from app.database import SessionLocal

    with SessionLocal() as db:
        review_id = create_record(db, "API-M5-HEARTBEAT", "职责主体明确。")
    app.dependency_overrides[get_chat_provider] = lambda: SlowProvider()
    monkeypatch.setattr("app.api.review_routes.SSE_HEARTBEAT_SECONDS", 0.01)
    try:
        response = reviewer_client.post(f"/api/v1/reviews/{review_id}/execute")
    finally:
        app.dependency_overrides.pop(get_chat_provider, None)

    assert response.status_code == 200
    assert "event: heartbeat" in response.text
    assert "event: completed" in response.text


def test_issue_actions_are_persisted_with_actor_and_do_not_leak_between_reports(reviewer_client):
    from app.database import SessionLocal

    with SessionLocal() as db:
        first_id = create_record(db, "API-M5-02", "第一份制度原文")
        second_id = create_record(db, "API-M5-03", "第二份制度原文")
        first_issue = ReviewIssue(
            review_record_id=first_id,
            dimension="rule",
            original="第一份制度原文",
            location="第一条",
            explanation="编号错误",
            consequence="引用困难",
            suggestion="修改编号",
            details={"rule_category": "条款编号"},
        )
        second_issue = ReviewIssue(
            review_record_id=second_id,
            dimension="semantic",
            original="第二份制度原文",
            location="第二条",
            explanation="语义问题",
            consequence="执行不一",
            suggestion="明确表述",
            details={"ambiguous_expression": "适当"},
        )
        db.add_all([first_issue, second_issue])
        db.commit()
        db.refresh(first_issue)
        issue_id = first_issue.id

    report_issues = reviewer_client.get(f"/api/v1/reviews/{first_id}/issues").json()
    assert [item["original"] for item in report_issues] == ["第一份制度原文"]

    action = reviewer_client.post(
        f"/api/v1/reviews/issues/{issue_id}/actions",
        json={"action": "补充处理意见", "opinion": "请业务部门确认。"},
    )
    adopted = reviewer_client.post(
        f"/api/v1/reviews/issues/{issue_id}/actions",
        json={"action": "采纳修改建议"},
    )

    assert action.status_code == 200
    assert adopted.status_code == 200
    assert adopted.json()["status"] == "已采纳"
    assert [item["action"] for item in adopted.json()["histories"]] == [
        "补充处理意见",
        "采纳修改建议",
    ]
    assert adopted.json()["histories"][0]["actor_name"] == "李明"


def test_supplement_action_requires_an_opinion(reviewer_client):
    from app.database import SessionLocal

    with SessionLocal() as db:
        review_id = create_record(db, "API-M5-04")
        issue = ReviewIssue(
            review_record_id=review_id,
            dimension="semantic",
            original="原文",
            location="第一条",
            explanation="说明",
            consequence="后果",
            suggestion="建议",
            details={},
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)
        issue_id = issue.id

    response = reviewer_client.post(
        f"/api/v1/reviews/issues/{issue_id}/actions",
        json={"action": "补充处理意见", "opinion": "   "},
    )

    assert response.status_code == 422

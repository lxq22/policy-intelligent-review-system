from app import models, schemas


def test_review_issue_and_history_are_persisted_and_serialized(db):
    issue_model = getattr(models, "ReviewIssue", None)
    history_model = getattr(models, "ReviewIssueHistory", None)
    issue_schema = getattr(schemas, "ReviewIssueOut", None)

    assert issue_model is not None
    assert history_model is not None
    assert issue_schema is not None

    user = models.User(
        username="m5-reviewer",
        password_hash="unused",
        name="审查人员甲",
        role="reviewer",
    )
    record = models.ReviewRecord(
        record_code="测试制度-0001",
        regulation_name="测试制度",
        dimensions=["semantic"],
        source_snapshot=[],
        candidate_snapshot=[],
        created_by=1,
    )
    db.add(user)
    db.flush()
    record.created_by = user.id
    db.add(record)
    db.flush()

    issue = issue_model(
        review_record_id=record.id,
        dimension="semantic",
        original="相关部门应及时处理。",
        location="第三条",
        explanation="“及时”缺少明确期限。",
        consequence="执行期限不统一。",
        suggestion="明确为收到申请后 3 个工作日内处理。",
        insufficient_evidence=True,
        details={"ambiguous_expression": "及时"},
    )
    db.add(issue)
    db.flush()
    issue.histories.append(
        history_model(
            actor_id=user.id,
            actor_name=user.name,
            action="补充处理意见",
            opinion="由业务部门确认具体期限。",
        )
    )
    db.commit()
    db.refresh(issue)

    result = issue_schema.model_validate(issue)

    assert issue.review_record_id == record.id
    assert result.dimension == "semantic"
    assert result.evidence_status == "证据不足，请人工判断"
    assert result.details["ambiguous_expression"] == "及时"
    assert result.histories[0].actor_name == "审查人员甲"
    assert result.histories[0].action == "补充处理意见"


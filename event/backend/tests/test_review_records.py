from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Clause


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = (
    REPOSITORY_ROOT
    / "制度审查测试数据集"
    / "生成文件"
    / "待审查_重大事项管理_含流程冲突.docx"
)
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def prepare_related_regulations(client):
    department_id = client.get("/api/v1/master-data/departments").json()[0]["id"]
    results = []
    for name in ("审查记录待审制度", "审查记录对比制度"):
        regulation = client.post(
            "/api/v1/regulations",
            json={"name": name, "department_id": department_id, "status": "生效中"},
        ).json()
        uploaded = client.post(
            f"/api/v1/regulations/{regulation['id']}/versions/upload",
            files={"file": (FIXTURE.name, FIXTURE.read_bytes(), DOCX_MIME)},
            data={"version": "V1.0"},
        )
        assert uploaded.status_code == 201
        clauses = client.get(f"/api/v1/regulations/{regulation['id']}/clauses").json()
        results.append((regulation, uploaded.json(), clauses))
    return results


def create_review(client, source, **overrides):
    payload = {
        "source_type": "regulation",
        "regulation_id": source[0]["id"],
        "clause_ids": [source[2][0]["id"]],
        "dimensions": ["semantic", "rule"],
        "candidate_clause_ids": [],
        "comparison_regulation_ids": [],
    }
    payload.update(overrides)
    return client.post("/api/v1/reviews", json=payload)


def test_repeated_review_gets_independent_number_and_immutable_snapshot(reviewer_client):
    source, _ = prepare_related_regulations(reviewer_client)

    first = create_review(reviewer_client, source)
    second = create_review(reviewer_client, source)

    assert first.status_code == 201
    assert second.status_code == 201
    first_data = first.json()
    second_data = second.json()
    assert first_data["record_code"].endswith("-01")
    assert second_data["record_code"].endswith("-02")
    assert first_data["id"] != second_data["id"]
    assert "status" not in first_data
    assert "task_name" not in first_data
    assert first_data["source_snapshot"][0]["text"]


def test_review_rejects_invalid_dimension_and_foreign_source_clause(reviewer_client):
    source, comparison = prepare_related_regulations(reviewer_client)

    invalid_dimension = create_review(
        reviewer_client, source, dimensions=["unknown"]
    )
    foreign_clause = create_review(
        reviewer_client,
        source,
        clause_ids=[comparison[2][0]["id"]],
    )

    assert invalid_dimension.status_code == 422
    assert foreign_clause.status_code == 422
    assert "不属于" in foreign_clause.json()["error"]["message"]


def test_conflict_requires_valid_scoped_candidate_clause(reviewer_client):
    source, comparison = prepare_related_regulations(reviewer_client)
    missing = create_review(reviewer_client, source, dimensions=["conflict"])
    valid = create_review(
        reviewer_client,
        source,
        dimensions=["conflict"],
        candidate_clause_ids=[comparison[2][0]["id"]],
    )

    assert missing.status_code == 422
    assert "候选" in missing.json()["error"]["message"]
    assert valid.status_code == 201
    assert valid.json()["candidate_snapshot"][0]["clause_id"] == comparison[2][0]["id"]


def test_non_conflict_review_ignores_candidate_input(reviewer_client):
    source, _ = prepare_related_regulations(reviewer_client)

    response = create_review(
        reviewer_client,
        source,
        dimensions=["semantic"],
        candidate_clause_ids=[999999],
    )

    assert response.status_code == 201
    assert response.json()["candidate_snapshot"] == []


def test_historical_snapshot_survives_source_clause_change(reviewer_client):
    source, _ = prepare_related_regulations(reviewer_client)
    created = create_review(reviewer_client, source).json()
    original_text = created["source_snapshot"][0]["text"]

    with SessionLocal() as db:
        clause = db.scalar(select(Clause).where(Clause.id == source[2][0]["id"]))
        clause.content = "后续修订后的新条文"
        db.commit()

    detail = reviewer_client.get(f"/api/v1/reviews/{created['id']}")

    assert detail.status_code == 200
    assert detail.json()["source_snapshot"][0]["text"] == original_text
    assert detail.json()["source_snapshot"][0]["text"] != "后续修订后的新条文"


def test_review_records_can_be_listed(reviewer_client):
    source, _ = prepare_related_regulations(reviewer_client)
    created = create_review(reviewer_client, source).json()

    response = reviewer_client.get("/api/v1/reviews")

    assert response.status_code == 200
    assert created["id"] in {item["id"] for item in response.json()}

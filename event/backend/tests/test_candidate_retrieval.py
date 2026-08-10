import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models import (
    Clause,
    Department,
    ManualRelation,
    Regulation,
    RegulationVersion,
    TemporaryReviewFile,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "制度审查测试数据集" / "生成文件"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def retrieval_api():
    try:
        ranking = importlib.import_module("app.retrieval.ranking")
        embeddings = importlib.import_module("app.retrieval.embeddings")
        candidates = importlib.import_module("app.services.candidates")
    except ImportError as exc:
        pytest.fail(f"M4 候选条款检索尚未实现：{exc}")
    return ranking, embeddings, candidates


def test_rrf_merges_and_labels_keyword_and_vector_evidence():
    ranking, _, _ = retrieval_api()

    result = ranking.rrf([10, 20], [20, 30], k=60)

    assert [item[0] for item in result] == [20, 10, 30]
    assert result[0][2] == ["关键词", "向量"]


def test_deterministic_embedding_has_256_normalized_values():
    _, embeddings, _ = retrieval_api()
    provider = embeddings.DeterministicEmbeddingProvider()

    first = provider.embed("重大事项应当经集体决策")
    second = provider.embed("重大事项应当经集体决策")

    assert provider.model_name == "local-hash-zh-v1"
    assert first == second
    assert len(first) == 256
    assert sum(value * value for value in first) == pytest.approx(1.0)


def add_parsed_regulation(
    db,
    embeddings,
    *,
    name,
    department_id,
    text,
    parse_status="解析成功",
    deleted=False,
):
    regulation = Regulation(
        name=name,
        department_id=department_id,
        parse_status=parse_status,
        deleted_at=datetime.now(UTC).replace(tzinfo=None) if deleted else None,
    )
    db.add(regulation)
    db.flush()
    version = RegulationVersion(
        regulation_id=regulation.id,
        version="V1.0",
        parse_status=parse_status,
    )
    db.add(version)
    db.flush()
    clause = Clause(
        regulation_version_id=version.id,
        sequence=1,
        original_no="第一条",
        title="",
        content=text,
        level="article",
        heading_path=["第一章 总则"],
        paragraph_start=1,
        paragraph_end=1,
        embedding=embeddings.DeterministicEmbeddingProvider().embed(text),
    )
    db.add(clause)
    db.flush()
    return regulation, clause


def test_formal_candidates_are_limited_to_visible_active_parsed_relations(db):
    _, embeddings, candidates = retrieval_api()
    related_department = Department(name="同一部门")
    other_department = Department(name="其他部门")
    db.add_all([related_department, other_department])
    db.flush()
    source, source_clause = add_parsed_regulation(
        db,
        embeddings,
        name="待审制度",
        department_id=related_department.id,
        text="重大事项应当经集体决策。",
    )
    automatic, automatic_clause = add_parsed_regulation(
        db,
        embeddings,
        name="自动关联制度",
        department_id=related_department.id,
        text="重大事项须经集体审议决定。",
    )
    manual, manual_clause = add_parsed_regulation(
        db,
        embeddings,
        name="手工关联制度",
        department_id=other_department.id,
        text="重大事项履行会议决策程序。",
    )
    unrelated, _ = add_parsed_regulation(
        db,
        embeddings,
        name="无关制度",
        department_id=other_department.id,
        text="重大事项无须审批。",
    )
    failed, _ = add_parsed_regulation(
        db,
        embeddings,
        name="解析失败制度",
        department_id=related_department.id,
        text="重大事项由个人决定。",
        parse_status="解析失败",
    )
    deleted, _ = add_parsed_regulation(
        db,
        embeddings,
        name="已删除制度",
        department_id=related_department.id,
        text="重大事项直接办理。",
        deleted=True,
    )
    db.add(
        ManualRelation(
            source_id=source.id,
            target_id=manual.id,
            relation_type="关联",
            source_kind="手工添加",
        )
    )
    db.commit()

    result = candidates.CandidateService().for_regulation(
        db, source.id, [source_clause.id]
    )

    ids = {item.clause_id for item in result}
    assert {automatic_clause.id, manual_clause.id}.issubset(ids)
    excluded_regulations = {unrelated.id, failed.id, deleted.id, source.id}
    assert not excluded_regulations.intersection({item.regulation_id for item in result})


def test_temporary_candidates_search_only_selected_comparison_regulations(db):
    _, embeddings, candidates = retrieval_api()
    department = Department(name="制度部门")
    db.add(department)
    db.flush()
    selected, selected_clause = add_parsed_regulation(
        db,
        embeddings,
        name="已选制度",
        department_id=department.id,
        text="资金事项应当提交会议审议。",
    )
    unselected, _ = add_parsed_regulation(
        db,
        embeddings,
        name="未选制度",
        department_id=department.id,
        text="资金事项由负责人审批。",
    )
    temporary = TemporaryReviewFile(
        original_name="临时制度.docx",
        stored_path="temporary/source.docx",
        file_size=1,
        sha256="0" * 64,
        parse_status="解析成功",
    )
    db.add(temporary)
    db.flush()
    source_clause = Clause(
        temporary_file_id=temporary.id,
        sequence=1,
        original_no="第一条",
        title="",
        content="资金事项须履行审议程序。",
        level="article",
        heading_path=[],
        paragraph_start=1,
        paragraph_end=1,
        embedding=embeddings.DeterministicEmbeddingProvider().embed("资金事项须履行审议程序。"),
    )
    db.add(source_clause)
    db.commit()

    result = candidates.CandidateService().for_temporary(
        db, temporary.id, [source_clause.id], [selected.id]
    )

    assert {item.clause_id for item in result} == {selected_clause.id}
    assert unselected.id not in {item.regulation_id for item in result}


def test_source_clause_ownership_is_validated(db):
    _, embeddings, candidates = retrieval_api()
    department = Department(name="部门")
    db.add(department)
    db.flush()
    source, _ = add_parsed_regulation(
        db, embeddings, name="制度甲", department_id=department.id, text="条款甲"
    )
    _, foreign_clause = add_parsed_regulation(
        db, embeddings, name="制度乙", department_id=department.id, text="条款乙"
    )
    db.commit()

    with pytest.raises(ValueError, match="不属于"):
        candidates.CandidateService().for_regulation(db, source.id, [foreign_clause.id])


def test_candidate_api_returns_related_policy_clauses(reviewer_client):
    department_id = reviewer_client.get("/api/v1/master-data/departments").json()[0]["id"]
    fixture = FIXTURE_ROOT / "待审查_重大事项管理_含流程冲突.docx"
    regulation_ids = []
    clause_ids = []
    for name in ("候选接口待审制度", "候选接口关联制度"):
        regulation = reviewer_client.post(
            "/api/v1/regulations",
            json={"name": name, "department_id": department_id, "status": "生效中"},
        ).json()
        regulation_ids.append(regulation["id"])
        upload = reviewer_client.post(
            f"/api/v1/regulations/{regulation['id']}/versions/upload",
            files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
            data={"version": "V1.0"},
        )
        assert upload.status_code == 201
        clauses = reviewer_client.get(
            f"/api/v1/regulations/{regulation['id']}/clauses"
        ).json()
        clause_ids.append(clauses[0]["id"])

    response = reviewer_client.post(
        "/api/v1/reviews/candidates",
        json={
            "source_type": "regulation",
            "regulation_id": regulation_ids[0],
            "clause_ids": [clause_ids[0]],
            "comparison_regulation_ids": [],
        },
    )

    assert response.status_code == 200
    assert regulation_ids[1] in {item["regulation_id"] for item in response.json()}

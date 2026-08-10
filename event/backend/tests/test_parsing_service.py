import hashlib
import importlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.models import Regulation, RegulationVersion
from app.parsers import DocumentParseError


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "制度审查测试数据集" / "生成文件"


def m4_api():
    try:
        storage = importlib.import_module("app.services.file_storage")
        parsing = importlib.import_module("app.services.parsing")
        models = importlib.import_module("app.models")
    except (ImportError, AttributeError) as exc:
        pytest.fail(f"M4 持久化服务尚未实现：{exc}")
    return storage, parsing, models


def upload_for(path: Path) -> UploadFile:
    mime = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if path.suffix == ".docx"
        else "application/pdf"
    )
    return UploadFile(
        file=BytesIO(path.read_bytes()),
        filename=path.name,
        headers=Headers({"content-type": mime}),
    )


def create_version(db, stored):
    regulation = Regulation(name="综合审查样例", parse_status="待解析")
    db.add(regulation)
    db.flush()
    version = RegulationVersion(
        regulation_id=regulation.id,
        version="V1.0",
        file_name=stored.original_name,
        stored_path=stored.relative_path,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        parse_status="待解析",
    )
    db.add(version)
    db.commit()
    return version


def test_file_storage_uses_safe_generated_path_and_records_digest(tmp_path):
    storage, _, _ = m4_api()
    payload = b"policy-content"
    upload = UploadFile(
        file=BytesIO(payload),
        filename="../敏感 名称.docx",
        headers=Headers(
            {
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            }
        ),
    )

    stored = storage.FileStorage(tmp_path).save(upload, "versions/7")

    resolved = (tmp_path / stored.relative_path).resolve()
    assert resolved.is_relative_to(tmp_path.resolve())
    assert resolved.read_bytes() == payload
    assert stored.original_name == "敏感 名称.docx"
    assert stored.sha256 == hashlib.sha256(payload).hexdigest()
    assert Path(stored.relative_path).name != stored.original_name


def test_successful_parse_persists_clauses_metadata_and_vectors(db, tmp_path):
    storage, parsing, models = m4_api()
    fixture = FIXTURE_ROOT / "待审查_综合审查样例.docx"
    stored = storage.FileStorage(tmp_path).save(upload_for(fixture), "versions")
    version = create_version(db, stored)

    clauses = parsing.ParseService(tmp_path).parse_version(db, version.id)

    db.refresh(version)
    assert version.parse_status == "解析成功"
    assert version.parse_error is None
    assert len(clauses) == 13
    assert clauses[8].original_no == "第九条"
    assert clauses[8].heading_path == ["第三章 审批与备案"]
    assert len(clauses[0].embedding) == 256
    assert db.query(models.Clause).filter_by(regulation_version_id=version.id).count() == 13


def test_successful_reparse_atomically_replaces_clauses(db, tmp_path):
    storage, parsing, models = m4_api()
    store = storage.FileStorage(tmp_path)
    first = FIXTURE_ROOT / "待审查_综合审查样例.docx"
    second = FIXTURE_ROOT / "待审查_重大事项管理_含流程冲突.docx"
    stored = store.save(upload_for(first), "versions")
    version = create_version(db, stored)
    service = parsing.ParseService(tmp_path)
    original = service.parse_version(db, version.id)
    old_ids = {item.id for item in original}

    replacement = store.save(upload_for(second), "versions")
    for key, value in {
        "file_name": replacement.original_name,
        "stored_path": replacement.relative_path,
        "mime_type": replacement.mime_type,
        "file_size": replacement.size,
        "sha256": replacement.sha256,
    }.items():
        setattr(version, key, value)
    db.commit()
    result = service.parse_version(db, version.id)

    assert len(result) == 10
    assert not old_ids.intersection({item.id for item in result})
    assert db.query(models.Clause).filter_by(regulation_version_id=version.id).count() == 10


def test_failed_reparse_preserves_previous_successful_clauses(db, tmp_path):
    storage, parsing, models = m4_api()
    store = storage.FileStorage(tmp_path)
    fixture = FIXTURE_ROOT / "待审查_综合审查样例.docx"
    stored = store.save(upload_for(fixture), "versions")
    version = create_version(db, stored)
    service = parsing.ParseService(tmp_path)
    old_ids = {item.id for item in service.parse_version(db, version.id)}

    broken = tmp_path / "broken.docx"
    broken.write_bytes(b"broken")
    version.stored_path = str(broken.relative_to(tmp_path))
    db.commit()

    with pytest.raises(DocumentParseError, match="无法解析"):
        service.parse_version(db, version.id)

    db.refresh(version)
    remaining_ids = {
        item.id
        for item in db.query(models.Clause)
        .filter_by(regulation_version_id=version.id)
        .all()
    }
    assert remaining_ids == old_ids
    assert version.parse_status == "解析成功"
    assert "无法解析" in version.parse_error


def test_first_parse_failure_is_recorded(db, tmp_path):
    _, parsing, _ = m4_api()
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"broken")
    regulation = Regulation(name="损坏文件", parse_status="待解析")
    db.add(regulation)
    db.flush()
    version = RegulationVersion(
        regulation_id=regulation.id,
        stored_path="broken.pdf",
        file_name="broken.pdf",
        parse_status="待解析",
    )
    db.add(version)
    db.commit()

    with pytest.raises(Exception, match="无法解析"):
        parsing.ParseService(tmp_path).parse_version(db, version.id)

    db.refresh(version)
    assert version.parse_status == "解析失败"
    assert "无法解析" in version.parse_error


def test_temporary_file_clauses_are_isolated_from_regulation_versions(db, tmp_path):
    storage, parsing, models = m4_api()
    fixture = FIXTURE_ROOT / "待审查_重大事项管理_含流程冲突.pdf"
    stored = storage.FileStorage(tmp_path).save(upload_for(fixture), "temporary")
    temporary = models.TemporaryReviewFile(
        original_name=stored.original_name,
        stored_path=stored.relative_path,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        parse_status="待解析",
    )
    db.add(temporary)
    db.commit()

    clauses = parsing.ParseService(tmp_path).parse_temporary_file(db, temporary.id)

    assert clauses
    assert all(item.temporary_file_id == temporary.id for item in clauses)
    assert all(item.regulation_version_id is None for item in clauses)
    assert db.query(RegulationVersion).count() == 0

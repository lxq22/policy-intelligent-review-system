from io import BytesIO
from pathlib import Path

import fitz


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPOSITORY_ROOT / "制度审查测试数据集" / "生成文件"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def create_regulation(client, name="待上传制度"):
    response = client.post(
        "/api/v1/regulations",
        json={"name": name, "version": "V0", "status": "生效中"},
    )
    assert response.status_code == 201
    return response.json()


def test_temporary_upload_parses_but_never_appears_in_regulation_list(reviewer_client):
    fixture = FIXTURE_ROOT / "待审查_重大事项管理_含流程冲突.docx"
    response = reviewer_client.post(
        "/api/v1/temporary-files",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
    )

    assert response.status_code == 201
    temporary = response.json()
    assert temporary["parse_status"] == "解析成功"
    clauses = reviewer_client.get(
        f"/api/v1/temporary-files/{temporary['id']}/clauses"
    ).json()
    assert len(clauses) == 10
    names = [item["name"] for item in reviewer_client.get("/api/v1/regulations").json()]
    assert temporary["original_name"] not in names


def test_formal_upload_requires_upload_permission(limited_client):
    response = limited_client.post(
        "/api/v1/regulations/1/versions/upload",
        files={"file": ("制度.docx", b"content", DOCX_MIME)},
        data={"version": "V2"},
    )

    assert response.status_code == 403


def test_formal_upload_parses_and_lists_current_version_clauses(reviewer_client):
    regulation = create_regulation(reviewer_client)
    fixture = FIXTURE_ROOT / "待审查_综合审查样例.docx"
    response = reviewer_client.post(
        f"/api/v1/regulations/{regulation['id']}/versions/upload",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
        data={"version": "V1.0", "note": "M4 测试上传"},
    )

    assert response.status_code == 201
    version = response.json()
    assert version["parse_status"] == "解析成功"
    assert version["sha256"]
    clauses = reviewer_client.get(
        f"/api/v1/regulations/{regulation['id']}/clauses"
    ).json()
    assert len(clauses) == 13
    assert clauses[8]["original_no"] == "第九条"


def test_create_regulation_with_file_parses_initial_version(reviewer_client):
    fixture = FIXTURE_ROOT / "待审查_综合审查样例.docx"

    response = reviewer_client.post(
        "/api/v1/regulations/with-file",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
        data={
            "name": "一体化上传制度",
            "code": "TEST-001",
            "version": "V1.0",
            "hierarchy": "二级单位制度",
            "status": "生效中",
            "scope": "当前单位",
        },
    )

    assert response.status_code == 201
    regulation = response.json()
    assert regulation["name"] == "一体化上传制度"
    assert regulation["file_name"] == fixture.name
    assert regulation["parse_status"] == "解析成功"
    assert regulation["versions"][0]["parse_status"] == "解析成功"
    clauses = reviewer_client.get(
        f"/api/v1/regulations/{regulation['id']}/clauses"
    ).json()
    assert len(clauses) == 13


def test_create_regulation_with_file_requires_upload_permission(limited_client):
    fixture = FIXTURE_ROOT / "待审查_综合审查样例.docx"

    response = limited_client.post(
        "/api/v1/regulations/with-file",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
        data={"name": "无权限制度", "version": "V1.0"},
    )

    assert response.status_code == 403


def test_create_regulation_with_file_removes_failed_parse(reviewer_client):
    buffer = BytesIO()
    with fitz.open() as document:
        document.new_page()
        document.save(buffer)

    before = {
        item["name"] for item in reviewer_client.get("/api/v1/regulations").json()
    }
    response = reviewer_client.post(
        "/api/v1/regulations/with-file",
        files={"file": ("扫描制度.pdf", buffer.getvalue(), "application/pdf")},
        data={"name": "不应残留的制度", "version": "V1.0"},
    )
    after = {
        item["name"] for item in reviewer_client.get("/api/v1/regulations").json()
    }

    assert response.status_code == 422
    assert "扫描" in response.json()["error"]["message"]
    assert after == before


def test_reparse_endpoints_return_current_parsed_content(reviewer_client):
    regulation = create_regulation(reviewer_client, "重新解析制度")
    fixture = FIXTURE_ROOT / "待审查_资金与关联交易_含关联冲突.docx"
    uploaded = reviewer_client.post(
        f"/api/v1/regulations/{regulation['id']}/versions/upload",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
        data={"version": "V1.0"},
    ).json()
    formal = reviewer_client.post(
        f"/api/v1/regulation-versions/{uploaded['id']}/reparse"
    )
    temporary = reviewer_client.post(
        "/api/v1/temporary-files",
        files={"file": (fixture.name, fixture.read_bytes(), DOCX_MIME)},
    ).json()
    temporary_reparse = reviewer_client.post(
        f"/api/v1/temporary-files/{temporary['id']}/reparse"
    )

    assert formal.status_code == 200
    assert formal.json()["parse_status"] == "解析成功"
    assert temporary_reparse.status_code == 200
    assert temporary_reparse.json()["parse_status"] == "解析成功"


def test_unsupported_extension_returns_readable_error(reviewer_client):
    response = reviewer_client.post(
        "/api/v1/temporary-files",
        files={"file": ("制度.txt", b"text", "text/plain")},
    )

    assert response.status_code == 422
    assert "仅支持" in response.json()["error"]["message"]


def test_text_empty_pdf_returns_scanned_pdf_error(reviewer_client):
    buffer = BytesIO()
    with fitz.open() as document:
        document.new_page()
        document.save(buffer)

    response = reviewer_client.post(
        "/api/v1/temporary-files",
        files={"file": ("扫描制度.pdf", buffer.getvalue(), "application/pdf")},
    )

    assert response.status_code == 422
    assert "扫描" in response.json()["error"]["message"]

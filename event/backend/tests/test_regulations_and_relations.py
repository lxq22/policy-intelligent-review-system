def test_regulation_search_create_update_version_delete_and_restore(reviewer_client):
    departments = reviewer_client.get("/api/v1/master-data/departments").json()
    categories = reviewer_client.get("/api/v1/master-data/categories").json()
    units = reviewer_client.get("/api/v1/master-data/units").json()

    create = reviewer_client.post(
        "/api/v1/regulations",
        json={
            "name": "测试制度",
            "code": "TEST-01",
            "department_id": departments[0]["id"],
            "category_id": categories[0]["id"],
            "unit_id": units[0]["id"],
            "hierarchy": "一级单位制度",
            "version": "V1.0",
            "status": "生效中",
            "file_name": "测试制度.docx",
        },
    )
    assert create.status_code == 201
    created = create.json()

    found = reviewer_client.get("/api/v1/regulations", params={"name": "测试制度"}).json()
    assert [item["id"] for item in found] == [created["id"]]

    update = reviewer_client.patch(
        f"/api/v1/regulations/{created['id']}",
        json={"scope": "更新后的适用范围", "status": "已失效"},
    )
    assert update.status_code == 200
    assert update.json()["scope"] == "更新后的适用范围"

    version = reviewer_client.post(
        f"/api/v1/regulations/{created['id']}/versions",
        json={"version": "V2.0", "file_name": "测试制度V2.0.pdf"},
    )
    assert version.status_code == 201
    detail = reviewer_client.get(f"/api/v1/regulations/{created['id']}").json()
    assert detail["version"] == "V2.0"
    assert len(detail["versions"]) == 2

    deleted = reviewer_client.delete(f"/api/v1/regulations/{created['id']}")
    assert deleted.status_code == 204
    assert reviewer_client.get(f"/api/v1/regulations/{created['id']}").status_code == 404

    reviewer_client.post("/api/v1/auth/logout")
    assert reviewer_client.post("/api/v1/auth/login", json={"username": "admin", "password": "demo123"}).status_code == 200
    deleted_items = reviewer_client.get("/api/v1/admin/deleted-regulations").json()
    assert created["id"] in [item["id"] for item in deleted_items]
    restored = reviewer_client.post(f"/api/v1/admin/regulations/{created['id']}/restore")
    assert restored.status_code == 200


def test_automatic_manual_and_reverse_relations(reviewer_client):
    items = reviewer_client.get("/api/v1/regulations").json()
    implementation = next(item for item in items if item["name"] == "采购管理实施细则")
    policy = next(item for item in items if item["name"] == "采购管理办法")
    supplier = next(item for item in items if item["name"] == "供应商管理规定")

    detail = reviewer_client.get(f"/api/v1/regulations/{implementation['id']}").json()
    automatic = {(item["type"], item["target_name"], item["source"]) for item in detail["relations"]}
    assert ("上位", "采购管理办法", "系统自动") in automatic
    assert ("关联", "采购管理办法", "系统自动") in automatic
    assert ("引用", "供应商管理规定", "人工确认") in automatic

    add = reviewer_client.post(
        f"/api/v1/regulations/{policy['id']}/relations",
        json={"target_id": supplier["id"], "type": "引用", "note": "测试手工引用"},
    )
    assert add.status_code == 201
    duplicate = reviewer_client.post(
        f"/api/v1/regulations/{policy['id']}/relations",
        json={"target_id": supplier["id"], "type": "引用", "note": "重复关系不应再次保存"},
    )
    assert duplicate.status_code == 201
    assert len([item for item in duplicate.json() if item["type"] == "引用" and item["target_id"] == supplier["id"]]) == 1
    supplier_detail = reviewer_client.get(f"/api/v1/regulations/{supplier['id']}").json()
    reverse = next(item for item in supplier_detail["relations"] if item["type"] == "被引用" and item["target_id"] == policy["id"])
    assert reviewer_client.delete(f"/api/v1/regulations/{supplier['id']}/relations/{reverse['id'].removeprefix('manual-')}").status_code == 204
    assert not any(item["target_id"] == policy["id"] and item["type"] == "被引用" for item in reviewer_client.get(f"/api/v1/regulations/{supplier['id']}").json()["relations"])


def test_relation_suggestion_must_be_confirmed(reviewer_client):
    source = next(item for item in reviewer_client.get("/api/v1/regulations").json() if item["name"] == "采购管理实施细则")
    suggestions = reviewer_client.get(f"/api/v1/regulations/{source['id']}/suggestions").json()
    matched = next(item for item in suggestions if item["target_id"] is not None)

    confirmed = reviewer_client.post(f"/api/v1/regulations/{source['id']}/suggestions/{matched['id']}/confirm")
    assert confirmed.status_code == 200
    assert any(item["target_id"] == matched["target_id"] and item["type"] == matched["type"] and item["source"] == "人工确认" for item in confirmed.json())
    assert matched["id"] not in [item["id"] for item in reviewer_client.get(f"/api/v1/regulations/{source['id']}/suggestions").json()]
    assert reviewer_client.post(f"/api/v1/regulations/{source['id']}/suggestions/{matched['id']}/confirm").status_code == 404


def test_master_data_write_requires_relation_permission(reviewer_client):
    department = reviewer_client.post("/api/v1/master-data/departments", json={"name": "新增部门"})
    assert department.status_code == 201
    existing_units = reviewer_client.get("/api/v1/master-data/units").json()
    primary = reviewer_client.post("/api/v1/master-data/units", json={"name": "新一级单位", "level": "一级单位"})
    assert primary.status_code == 201
    secondary = reviewer_client.post(
        "/api/v1/master-data/units",
        json={"name": "新二级单位", "level": "二级单位", "parent_id": primary.json()["id"]},
    )
    assert secondary.status_code == 201
    assert secondary.json()["parent_name"] == "新一级单位"
    assert reviewer_client.delete(f"/api/v1/master-data/units/{primary.json()['id']}").status_code == 409
    assert reviewer_client.patch(
        f"/api/v1/master-data/units/{primary.json()['id']}",
        json={"name": "错误降级", "level": "二级单位", "parent_id": existing_units[0]["id"]},
    ).status_code == 409
    assert reviewer_client.post("/api/v1/master-data/units", json={"name": "无归属二级单位", "level": "二级单位"}).status_code == 422
    assert reviewer_client.patch(
        f"/api/v1/master-data/units/{secondary.json()['id']}",
        json={"name": "更新后二级单位", "level": "二级单位", "parent_id": primary.json()["id"]},
    ).status_code == 200
    assert reviewer_client.delete(f"/api/v1/master-data/units/{secondary.json()['id']}").status_code == 204
    assert reviewer_client.delete(f"/api/v1/master-data/units/{secondary.json()['id']}").status_code == 404

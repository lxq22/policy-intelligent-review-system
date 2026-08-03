from .conftest import login


def test_login_success_error_and_disabled(client):
    assert login(client, "reviewer").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    wrong = login(client, "reviewer", "wrong")
    assert wrong.status_code == 401
    assert wrong.json()["error"]["message"] == "用户名或密码错误"

    disabled = login(client, "reviewer_disabled")
    assert disabled.status_code == 403
    assert "停用" in disabled.json()["error"]["message"]


def test_role_and_configurable_permission_boundaries(limited_client):
    regulations = limited_client.get("/api/v1/regulations")
    assert regulations.status_code == 200
    regulation_id = regulations.json()[0]["id"]

    create = limited_client.post("/api/v1/regulations", json={"name": "无权限新增"})
    assert create.status_code == 403

    delete = limited_client.delete(f"/api/v1/regulations/{regulation_id}")
    assert delete.status_code == 403

    relation = limited_client.post(
        f"/api/v1/regulations/{regulation_id}/relations",
        json={"target_id": regulations.json()[1]["id"], "type": "关联"},
    )
    assert relation.status_code == 403

    edit = limited_client.patch(f"/api/v1/regulations/{regulation_id}", json={"scope": "默认权限允许编辑"})
    assert edit.status_code == 200


def test_admin_cannot_enter_reviewer_business_api(admin_client):
    assert admin_client.get("/api/v1/regulations").status_code == 403
    assert admin_client.get("/api/v1/admin/users").status_code == 200

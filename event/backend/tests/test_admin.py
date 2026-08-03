from sqlalchemy import select

from app.database import SessionLocal
from app.models import ManualRelation, User


def test_admin_user_permissions_lifecycle(admin_client):
    created = admin_client.post(
        "/api/v1/admin/users",
        json={"username": "new_reviewer", "name": "新审查人员", "department": "制度审查室"},
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert created.json()["permissions"] == {"upload": False, "delete": False, "relation": False}

    updated = admin_client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"name": "已修改人员", "department": "合规管理部"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "已修改人员"
    assert updated.json()["department"] == "合规管理部"

    permissions = admin_client.put(
        f"/api/v1/admin/users/{user_id}/permissions",
        json={"upload": True, "delete": False, "relation": True},
    )
    assert permissions.status_code == 200
    assert permissions.json()["permissions"]["relation"] is True

    disabled = admin_client.patch(f"/api/v1/admin/users/{user_id}", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    reset = admin_client.post(f"/api/v1/admin/users/{user_id}/reset-password")
    assert reset.status_code == 200
    assert reset.json()["temporary_password"].startswith("demo-")

    assert admin_client.delete(f"/api/v1/admin/users/{user_id}").status_code == 204


def test_deleting_relation_creator_keeps_business_relation(admin_client):
    with SessionLocal() as db:
        reviewer = db.scalar(select(User).where(User.username == "reviewer"))
        relation = db.scalar(select(ManualRelation).where(ManualRelation.created_by == reviewer.id))
        reviewer_id = reviewer.id
        relation_id = relation.id

    assert admin_client.delete(f"/api/v1/admin/users/{reviewer_id}").status_code == 204

    with SessionLocal() as db:
        relation = db.get(ManualRelation, relation_id)
        assert relation is not None
        assert relation.created_by is None


def test_operation_history_only_three_types_and_cleanup(admin_client):
    logs = admin_client.get("/api/v1/admin/operation-logs")
    assert logs.status_code == 200
    assert {item["type"] for item in logs.json()} <= {"新增制度", "删除制度", "恢复制度"}

    target = next(item for item in logs.json() if item["report_count"] > 0)
    deleted = admin_client.delete(
        f"/api/v1/admin/operation-logs/{target['id']}",
        params={"delete_reports": True},
    )
    assert deleted.status_code == 204
    remaining = admin_client.get("/api/v1/admin/operation-logs").json()
    assert target["id"] not in [item["id"] for item in remaining]

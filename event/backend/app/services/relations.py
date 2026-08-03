from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import ManualRelation, Regulation, Unit
from ..schemas import RelationOut

REVERSE_TYPES = {
    "上位": "下位",
    "下位": "上位",
    "关联": "关联",
    "引用": "被引用",
    "被引用": "引用",
    "版本替代": "版本替代",
}


def _relation_key(relation_type: str, target_id: int) -> tuple[str, int]:
    return relation_type, target_id


def collect_relations(db: Session, regulation: Regulation) -> list[RelationOut]:
    results: list[RelationOut] = []
    seen: set[tuple[str, int]] = set()
    active = list(db.scalars(select(Regulation).where(Regulation.deleted_at.is_(None), Regulation.id != regulation.id)))

    if regulation.department_id:
        for target in active:
            if target.department_id == regulation.department_id:
                key = _relation_key("关联", target.id)
                if key not in seen:
                    results.append(RelationOut(id=f"auto-dept-{regulation.id}-{target.id}", type="关联", target_id=target.id, target_name=target.name or "未命名制度", source="系统自动", note="同一部门"))
                    seen.add(key)

    current_unit = db.get(Unit, regulation.unit_id) if regulation.unit_id else None
    if current_unit:
        for target in active:
            target_unit = db.get(Unit, target.unit_id) if target.unit_id else None
            relation_type = None
            if target_unit and target_unit.parent_id == current_unit.id:
                relation_type = "下位"
            elif current_unit.parent_id and target_unit and current_unit.parent_id == target_unit.id:
                relation_type = "上位"
            if relation_type:
                key = _relation_key(relation_type, target.id)
                if key not in seen:
                    results.append(RelationOut(id=f"auto-unit-{regulation.id}-{target.id}", type=relation_type, target_id=target.id, target_name=target.name or "未命名制度", source="系统自动", note="一级单位—所属二级单位"))
                    seen.add(key)

    manual = list(
        db.scalars(
            select(ManualRelation).where(
                or_(ManualRelation.source_id == regulation.id, ManualRelation.target_id == regulation.id)
            )
        )
    )
    for item in manual:
        if item.source_id == regulation.id:
            target_id = item.target_id
            relation_type = item.relation_type
        else:
            target_id = item.source_id
            relation_type = REVERSE_TYPES[item.relation_type]
        target = db.get(Regulation, target_id)
        if not target or target.deleted_at is not None:
            continue
        key = _relation_key(relation_type, target_id)
        if key in seen:
            continue
        results.append(
            RelationOut(
                id=f"manual-{item.id}",
                type=relation_type,
                target_id=target_id,
                target_name=target.name or "未命名制度",
                source=item.source_kind,
                note=item.note,
            )
        )
        seen.add(key)
    return results

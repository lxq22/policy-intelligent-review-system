from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import require_reviewer, reviewer_permission
from ..database import get_db
from ..models import (
    ManualRelation,
    OperationLog,
    Regulation,
    RegulationVersion,
    RelationSuggestion,
    User,
)
from ..schemas import (
    RegulationIn,
    RegulationOut,
    RelationCreate,
    RelationOut,
    SuggestionOut,
    VersionIn,
    VersionOut,
)
from ..serializers import regulation_out
from ..services.relations import collect_relations

router = APIRouter(prefix="/regulations", tags=["制度"])


def get_active_regulation(db: Session, regulation_id: int) -> Regulation:
    item = db.scalar(
        select(Regulation)
        .options(selectinload(Regulation.versions))
        .where(Regulation.id == regulation_id, Regulation.deleted_at.is_(None))
    )
    if not item:
        raise HTTPException(status_code=404, detail="制度不存在或已删除")
    return item


@router.get("", response_model=list[RegulationOut])
def list_regulations(
    name: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    hierarchy: str | None = Query(default=None),
    regulation_status: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    statement = select(Regulation).where(Regulation.deleted_at.is_(None)).order_by(Regulation.updated_at.desc())
    if name:
        statement = statement.where(Regulation.name.contains(name))
    if department_id:
        statement = statement.where(Regulation.department_id == department_id)
    if hierarchy:
        statement = statement.where(Regulation.hierarchy == hierarchy)
    if regulation_status:
        statement = statement.where(Regulation.status == regulation_status)
    return [regulation_out(db, item, include_details=True) for item in db.scalars(statement)]


@router.post("", response_model=RegulationOut, status_code=201)
def create_regulation(
    payload: RegulationIn,
    user: User = Depends(reviewer_permission("upload")),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(exclude={"version"})
    item = Regulation(**values, current_version=payload.version, parse_status="待解析")
    db.add(item)
    db.flush()
    if payload.version or payload.file_name:
        db.add(RegulationVersion(regulation_id=item.id, version=payload.version, effective_date=payload.effective_date, file_name=payload.file_name, note="初始版本"))
    db.add(OperationLog(operation_type="新增制度", regulation_id=item.id, regulation_name=item.name, operator_id=user.id, operator_name=user.name))
    db.commit()
    return regulation_out(db, get_active_regulation(db, item.id), include_details=True)


@router.get("/{regulation_id}", response_model=RegulationOut)
def get_regulation(regulation_id: int, _: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    return regulation_out(db, get_active_regulation(db, regulation_id), include_details=True)


@router.patch("/{regulation_id}", response_model=RegulationOut)
def update_regulation(
    regulation_id: int,
    payload: RegulationIn,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    item = get_active_regulation(db, regulation_id)
    values = payload.model_dump(exclude_unset=True, exclude={"version", "file_name"})
    for key, value in values.items():
        setattr(item, key, value)
    if "version" in payload.model_fields_set:
        item.current_version = payload.version
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return regulation_out(db, get_active_regulation(db, item.id), include_details=True)


@router.delete("/{regulation_id}", status_code=204)
def delete_regulation(
    regulation_id: int,
    user: User = Depends(reviewer_permission("delete")),
    db: Session = Depends(get_db),
):
    item = get_active_regulation(db, regulation_id)
    item.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(OperationLog(operation_type="删除制度", regulation_id=item.id, regulation_name=item.name, operator_id=user.id, operator_name=user.name))
    db.commit()


@router.post("/{regulation_id}/versions", response_model=VersionOut, status_code=201)
def add_version(
    regulation_id: int,
    payload: VersionIn,
    _: User = Depends(reviewer_permission("upload")),
    db: Session = Depends(get_db),
):
    item = get_active_regulation(db, regulation_id)
    previous = item.current_version
    version = RegulationVersion(
        regulation_id=item.id,
        version=payload.version,
        effective_date=payload.effective_date,
        file_name=payload.file_name,
        note=payload.note or (f"替代 {previous}" if previous else None),
    )
    item.current_version = payload.version
    if payload.file_name:
        item.file_name = payload.file_name
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/{regulation_id}/relations", response_model=list[RelationOut])
def list_relations(regulation_id: int, _: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    return collect_relations(db, get_active_regulation(db, regulation_id))


@router.post("/{regulation_id}/relations", response_model=list[RelationOut], status_code=201)
def add_relation(
    regulation_id: int,
    payload: RelationCreate,
    user: User = Depends(reviewer_permission("relation")),
    db: Session = Depends(get_db),
):
    source = get_active_regulation(db, regulation_id)
    get_active_regulation(db, payload.target_id)
    if source.id == payload.target_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="不能与自身建立制度关系")
    already_visible = any(
        item.target_id == payload.target_id and item.type == payload.type
        for item in collect_relations(db, source)
    )
    if not already_visible:
        db.add(ManualRelation(source_id=source.id, target_id=payload.target_id, relation_type=payload.type, source_kind="手工添加", note=payload.note, created_by=user.id))
        db.commit()
    return collect_relations(db, source)


@router.delete("/{regulation_id}/relations/{relation_id}", status_code=204)
def delete_relation(
    regulation_id: int,
    relation_id: int,
    _: User = Depends(reviewer_permission("relation")),
    db: Session = Depends(get_db),
):
    get_active_regulation(db, regulation_id)
    item = db.get(ManualRelation, relation_id)
    if not item or regulation_id not in (item.source_id, item.target_id):
        raise HTTPException(status_code=404, detail="手工制度关系不存在")
    db.delete(item)
    db.commit()


@router.get("/{regulation_id}/suggestions", response_model=list[SuggestionOut])
def list_suggestions(regulation_id: int, _: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    get_active_regulation(db, regulation_id)
    items = db.scalars(select(RelationSuggestion).where(RelationSuggestion.source_id == regulation_id, RelationSuggestion.status == "待确认"))
    return [SuggestionOut(id=item.id, target_id=item.target_id, target_name=item.target_name, type=item.relation_type, evidence=item.evidence, status=item.status) for item in items]


@router.post("/{regulation_id}/suggestions/{suggestion_id}/confirm", response_model=list[RelationOut])
def confirm_suggestion(
    regulation_id: int,
    suggestion_id: int,
    user: User = Depends(reviewer_permission("relation")),
    db: Session = Depends(get_db),
):
    source = get_active_regulation(db, regulation_id)
    item = db.get(RelationSuggestion, suggestion_id)
    if not item or item.source_id != regulation_id or item.status != "待确认" or not item.target_id:
        raise HTTPException(status_code=404, detail="关系建议不存在或目标制度尚未匹配")
    get_active_regulation(db, item.target_id)
    already_visible = any(
        relation.target_id == item.target_id and relation.type == item.relation_type
        for relation in collect_relations(db, source)
    )
    if not already_visible:
        db.add(ManualRelation(source_id=regulation_id, target_id=item.target_id, relation_type=item.relation_type, source_kind="人工确认", note=item.evidence, created_by=user.id))
    item.status = "已确认"
    db.commit()
    return collect_relations(db, source)

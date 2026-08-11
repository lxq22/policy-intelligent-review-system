from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import require_reviewer, reviewer_permission
from ..database import get_db
from ..models import (
    ManualRelation,
    Clause,
    OperationLog,
    Regulation,
    RegulationVersion,
    RelationSuggestion,
    User,
)
from ..schemas import (
    RegulationIn,
    ClauseOut,
    RegulationOut,
    RelationCreate,
    RelationOut,
    SuggestionOut,
    VersionIn,
    VersionOut,
)
from ..config import get_settings
from ..parsers import DocumentParseError, UnsupportedDocumentError, parser_for
from ..serializers import regulation_out
from ..services.relations import collect_relations
from ..services.file_storage import FileStorage
from ..services.parsing import ParseService

router = APIRouter(prefix="/regulations", tags=["制度"])
settings = get_settings()


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


@router.post("/with-file", response_model=RegulationOut, status_code=201)
def create_regulation_with_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    code: str | None = Form(default=None),
    department_id: int | None = Form(default=None),
    category_id: int | None = Form(default=None),
    unit_id: int | None = Form(default=None),
    hierarchy: str | None = Form(default=None),
    version: str | None = Form(default=None),
    publish_date: date | None = Form(default=None),
    effective_date: date | None = Form(default=None),
    expiry_date: date | None = Form(default=None),
    regulation_status: str | None = Form(default=None, alias="status"),
    scope: str | None = Form(default=None),
    user: User = Depends(reviewer_permission("upload")),
    db: Session = Depends(get_db),
):
    try:
        parser_for(Path(file.filename or ""))
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    storage = FileStorage(settings.file_storage_root)
    item = Regulation(
        name=name,
        code=code,
        department_id=department_id,
        category_id=category_id,
        unit_id=unit_id,
        hierarchy=hierarchy,
        current_version=version,
        publish_date=publish_date,
        effective_date=effective_date,
        expiry_date=expiry_date,
        status=regulation_status,
        scope=scope,
        parse_status="待解析",
    )
    db.add(item)
    db.flush()
    stored = storage.save(file, f"regulations/{item.id}/versions")
    item.file_name = stored.original_name
    record = RegulationVersion(
        regulation_id=item.id,
        version=version,
        effective_date=effective_date,
        file_name=stored.original_name,
        stored_path=stored.relative_path,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        parse_status="待解析",
        note="初始版本",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        ParseService(settings.file_storage_root).parse_version(db, record.id)
    except (DocumentParseError, ValueError) as exc:
        failed = db.get(Regulation, item.id)
        if failed is not None:
            db.delete(failed)
            db.commit()
        storage.delete(stored.relative_path)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(
        OperationLog(
            operation_type="新增制度",
            regulation_id=item.id,
            regulation_name=item.name,
            operator_id=user.id,
            operator_name=user.name,
        )
    )
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


@router.post("/{regulation_id}/versions/upload", response_model=VersionOut, status_code=201)
def upload_version(
    regulation_id: int,
    file: UploadFile = File(...),
    version: str | None = Form(default=None),
    effective_date: date | None = Form(default=None),
    note: str | None = Form(default=None),
    _: User = Depends(reviewer_permission("upload")),
    db: Session = Depends(get_db),
):
    item = get_active_regulation(db, regulation_id)
    try:
        parser_for(Path(file.filename or ""))
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stored = FileStorage(settings.file_storage_root).save(file, f"regulations/{item.id}/versions")
    record = RegulationVersion(
        regulation_id=item.id,
        version=version,
        effective_date=effective_date,
        file_name=stored.original_name,
        stored_path=stored.relative_path,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        parse_status="待解析",
        note=note,
    )
    item.current_version = version
    item.effective_date = effective_date or item.effective_date
    item.file_name = stored.original_name
    item.parse_status = "待解析"
    db.add(record)
    db.commit()
    db.refresh(record)
    try:
        ParseService(settings.file_storage_root).parse_version(db, record.id)
    except (DocumentParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(record)
    return record


@router.get("/{regulation_id}/clauses", response_model=list[ClauseOut])
def list_regulation_clauses(
    regulation_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    get_active_regulation(db, regulation_id)
    version_id = db.scalar(
        select(RegulationVersion.id)
        .where(
            RegulationVersion.regulation_id == regulation_id,
            RegulationVersion.parse_status == "解析成功",
        )
        .order_by(RegulationVersion.id.desc())
        .limit(1)
    )
    if version_id is None:
        return []
    return list(
        db.scalars(
            select(Clause)
            .where(Clause.regulation_version_id == version_id)
            .order_by(Clause.sequence)
        )
    )


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

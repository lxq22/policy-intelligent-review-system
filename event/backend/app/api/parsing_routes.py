from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_reviewer, reviewer_permission
from ..config import get_settings
from ..database import get_db
from ..models import Clause, RegulationVersion, TemporaryReviewFile, User
from ..parsers import DocumentParseError, UnsupportedDocumentError, parser_for
from ..schemas import ClauseOut, TemporaryFileOut, VersionOut
from ..services.file_storage import FileStorage
from ..services.parsing import ParseService

router = APIRouter(tags=["文件解析"])
settings = get_settings()


def temporary_or_404(db: Session, file_id: int) -> TemporaryReviewFile:
    item = db.get(TemporaryReviewFile, file_id)
    if item is None:
        raise HTTPException(status_code=404, detail="临时待审文件不存在")
    return item


@router.post("/temporary-files", response_model=TemporaryFileOut, status_code=201)
def upload_temporary_file(
    file: UploadFile = File(...),
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    try:
        parser_for(Path(file.filename or ""))
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = FileStorage(settings.storage_root).save(file, "temporary")
    item = TemporaryReviewFile(
        original_name=stored.original_name,
        stored_path=stored.relative_path,
        mime_type=stored.mime_type,
        file_size=stored.size,
        sha256=stored.sha256,
        parse_status="待解析",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    try:
        ParseService(settings.storage_root).parse_temporary_file(db, item.id)
    except (DocumentParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(item)
    return item


@router.get("/temporary-files/{file_id}", response_model=TemporaryFileOut)
def get_temporary_file(
    file_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    return temporary_or_404(db, file_id)


@router.get("/temporary-files/{file_id}/clauses", response_model=list[ClauseOut])
def list_temporary_clauses(
    file_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    temporary_or_404(db, file_id)
    return list(
        db.scalars(
            select(Clause)
            .where(Clause.temporary_file_id == file_id)
            .order_by(Clause.sequence)
        )
    )


@router.post("/temporary-files/{file_id}/reparse", response_model=TemporaryFileOut)
def reparse_temporary_file(
    file_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    item = temporary_or_404(db, file_id)
    try:
        ParseService(settings.storage_root).parse_temporary_file(db, item.id)
    except (DocumentParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(item)
    return item


@router.post("/regulation-versions/{version_id}/reparse", response_model=VersionOut)
def reparse_regulation_version(
    version_id: int,
    _: User = Depends(reviewer_permission("upload")),
    db: Session = Depends(get_db),
):
    item = db.get(RegulationVersion, version_id)
    if item is None:
        raise HTTPException(status_code=404, detail="制度版本不存在")
    try:
        ParseService(settings.storage_root).parse_version(db, item.id)
    except (DocumentParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.refresh(item)
    return item

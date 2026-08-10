from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_reviewer
from ..database import get_db
from ..models import ReviewRecord, User
from ..schemas import CandidateClauseOut, CandidateRequest, ReviewCreate, ReviewRecordOut
from ..services.candidates import CandidateService
from ..services.reviews import ReviewService

router = APIRouter(prefix="/reviews", tags=["审查"])


@router.post("/candidates", response_model=list[CandidateClauseOut])
def retrieve_candidates(
    payload: CandidateRequest,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    service = CandidateService()
    try:
        if payload.source_type == "regulation":
            if payload.regulation_id is None:
                raise ValueError("正式制度审查必须指定待审制度")
            return service.for_regulation(db, payload.regulation_id, payload.clause_ids)
        if payload.temporary_file_id is None:
            raise ValueError("临时文件审查必须指定待审文件")
        return service.for_temporary(
            db,
            payload.temporary_file_id,
            payload.clause_ids,
            payload.comparison_regulation_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("", response_model=ReviewRecordOut, status_code=201)
def create_review(
    payload: ReviewCreate,
    user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    try:
        return ReviewService().create(db, user, payload)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[ReviewRecordOut])
def list_reviews(
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(ReviewRecord).order_by(ReviewRecord.created_at.desc())))


@router.get("/{review_id}", response_model=ReviewRecordOut)
def get_review(
    review_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    item = db.get(ReviewRecord, review_id)
    if item is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return item

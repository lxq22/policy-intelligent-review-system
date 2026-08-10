from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import require_reviewer
from ..database import get_db
from ..models import User
from ..schemas import CandidateClauseOut, CandidateRequest
from ..services.candidates import CandidateService

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

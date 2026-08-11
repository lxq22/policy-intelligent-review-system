import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import require_reviewer
from ..database import SessionLocal, get_db
from ..models import ReviewIssue, ReviewIssueHistory, ReviewRecord, User
from ..providers.chat import ChatProviderError, get_chat_provider
from ..schemas import (
    CandidateClauseOut,
    CandidateRequest,
    IssueActionIn,
    ReviewCreate,
    ReviewIssueOut,
    ReviewRecordOut,
)
from ..serializers import review_record_out
from ..services.candidates import CandidateService
from ..services.review_execution import ReviewExecutionError, ReviewExecutionService
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
        record = ReviewService().create(db, user, payload)
        return review_record_out(db, record)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[ReviewRecordOut])
def list_reviews(
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    records = list(
        db.scalars(select(ReviewRecord).order_by(ReviewRecord.created_at.desc()))
    )
    return [review_record_out(db, item) for item in records]


@router.get("/{review_id}", response_model=ReviewRecordOut)
def get_review(
    review_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    item = db.get(ReviewRecord, review_id)
    if item is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return review_record_out(db, item)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{review_id}/execute")
def execute_review(
    review_id: int,
    _: User = Depends(require_reviewer),
    provider=Depends(get_chat_provider),
    db: Session = Depends(get_db),
):
    if db.get(ReviewRecord, review_id) is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")

    def stream():
        events: Queue[tuple[str, dict]] = Queue()

        def progress(event: str, message: str) -> None:
            events.put((event, {"review_id": review_id, "message": message}))

        def run() -> None:
            with SessionLocal() as execution_db:
                try:
                    issues = ReviewExecutionService().execute(
                        execution_db, review_id, provider, progress
                    )
                    events.put(
                        (
                            "completed",
                            {"review_id": review_id, "problem_count": len(issues)},
                        )
                    )
                except (ReviewExecutionError, ChatProviderError) as exc:
                    events.put(("failed", {"review_id": review_id, "message": str(exc)}))
                except Exception:
                    events.put(
                        (
                            "failed",
                            {"review_id": review_id, "message": "审查执行失败，请稍后重试"},
                        )
                    )

        yield _sse("started", {"review_id": review_id, "message": "开始智能审查"})
        worker = Thread(target=run, daemon=True)
        worker.start()
        while True:
            event, data = events.get()
            yield _sse(event, data)
            if event in {"completed", "failed"}:
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{review_id}/issues", response_model=list[ReviewIssueOut])
def list_review_issues(
    review_id: int,
    _: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    if db.get(ReviewRecord, review_id) is None:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return list(
        db.scalars(
            select(ReviewIssue)
            .options(selectinload(ReviewIssue.histories))
            .where(ReviewIssue.review_record_id == review_id)
            .order_by(ReviewIssue.id)
        )
    )


@router.post("/issues/{issue_id}/actions", response_model=ReviewIssueOut)
def process_review_issue(
    issue_id: int,
    payload: IssueActionIn,
    user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    issue = db.scalar(
        select(ReviewIssue)
        .options(selectinload(ReviewIssue.histories))
        .where(ReviewIssue.id == issue_id)
    )
    if issue is None:
        raise HTTPException(status_code=404, detail="审查问题不存在")

    opinion = payload.opinion.strip() if payload.opinion else None
    if payload.action == "补充处理意见" and not opinion:
        raise HTTPException(status_code=422, detail="请填写处理意见")
    if payload.action == "采纳修改建议":
        issue.status = "已采纳"
    elif payload.action == "忽略":
        issue.status = "已忽略"
    else:
        issue.opinion = opinion

    issue.histories.append(
        ReviewIssueHistory(
            actor_id=user.id,
            actor_name=user.name or user.username,
            action=payload.action,
            opinion=opinion,
        )
    )
    db.commit()
    db.refresh(issue)
    return issue

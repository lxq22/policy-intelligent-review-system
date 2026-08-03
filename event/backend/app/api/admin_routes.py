from datetime import UTC, datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..auth import hash_password, require_admin
from ..database import get_db
from ..models import LoginSession, OperationLog, Regulation, ReviewRecord, User
from ..schemas import (
    OperationLogOut,
    PermissionUpdate,
    RegulationOut,
    ResetPasswordOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from ..serializers import operation_log_out, regulation_out, user_out

router = APIRouter(prefix="/admin", tags=["系统管理"])


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [user_out(item) for item in db.scalars(select(User).where(User.role == "reviewer").order_by(User.id))]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    initial_password = payload.password or "demo123"
    user = User(
        username=payload.username,
        password_hash=hash_password(initial_password),
        name=payload.name,
        department=payload.department,
        role="reviewer",
        enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.role != "reviewer":
        raise HTTPException(status_code=404, detail="审查人员不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    if payload.enabled is False:
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()
    return user_out(user)


@router.put("/users/{user_id}/permissions", response_model=UserOut)
def update_permissions(user_id: int, payload: PermissionUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.role != "reviewer":
        raise HTTPException(status_code=404, detail="审查人员不存在")
    user.perm_upload = payload.upload
    user.perm_delete = payload.delete
    user.perm_relation = payload.relation
    db.commit()
    return user_out(user)


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordOut)
def reset_password(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.role != "reviewer":
        raise HTTPException(status_code=404, detail="审查人员不存在")
    temporary = f"demo-{secrets.token_hex(3)}"
    user.password_hash = hash_password(temporary)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()
    return ResetPasswordOut(temporary_password=temporary)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user or user.role != "reviewer":
        raise HTTPException(status_code=404, detail="审查人员不存在")
    db.delete(user)
    db.commit()


@router.get("/deleted-regulations", response_model=list[RegulationOut])
def deleted_regulations(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Regulation)
        .options(selectinload(Regulation.versions))
        .where(Regulation.deleted_at.is_not(None))
        .order_by(Regulation.deleted_at.desc())
    )
    return [regulation_out(db, item) for item in items]


@router.post("/regulations/{regulation_id}/restore", response_model=RegulationOut)
def restore_regulation(regulation_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.scalar(
        select(Regulation)
        .options(selectinload(Regulation.versions))
        .where(Regulation.id == regulation_id, Regulation.deleted_at.is_not(None))
    )
    if not item:
        raise HTTPException(status_code=404, detail="已删除制度不存在")
    item.deleted_at = None
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(OperationLog(operation_type="恢复制度", regulation_id=item.id, regulation_name=item.name, operator_id=admin.id, operator_name=admin.name))
    db.commit()
    return regulation_out(db, item)


@router.get("/operation-logs", response_model=list[OperationLogOut])
def operation_logs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [operation_log_out(db, item) for item in db.scalars(select(OperationLog).order_by(OperationLog.operated_at.desc()))]


@router.delete("/operation-logs/{log_id}", status_code=204)
def delete_operation_log(
    log_id: int,
    delete_reports: bool = Query(default=False),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(OperationLog, log_id)
    if not item:
        raise HTTPException(status_code=404, detail="操作历史不存在")
    if delete_reports and item.regulation_id:
        db.execute(delete(ReviewRecord).where(ReviewRecord.regulation_id == item.regulation_id))
    db.delete(item)
    db.commit()

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    clear_login_session,
    create_login_session,
    get_current_user,
    settings,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, UserOut
from ..serializers import user_out

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已停用，请联系系统管理员")
    create_login_session(db, user, response)
    return user_out(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    raw_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> None:
    clear_login_session(db, response, raw_token)

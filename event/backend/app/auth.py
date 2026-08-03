import hashlib
import secrets

from fastapi import Cookie, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import LoginSession, User

password_hash = PasswordHash.recommended()
settings = get_settings()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_login_session(db: Session, user: User, response: Response) -> None:
    raw_token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_digest(raw_token), user_id=user.id))
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_login_session(db: Session, response: Response, raw_token: str | None) -> None:
    if raw_token:
        session = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(raw_token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


def get_current_user(
    db: Session = Depends(get_db),
    raw_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == token_digest(raw_token)))
    user = db.get(User, session.user_id) if session else None
    if not user or not user.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效或账号已停用")
    return user


def require_reviewer(user: User = Depends(get_current_user)) -> User:
    if user.role != "reviewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅审查人员可以执行此操作")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅系统管理员可以执行此操作")
    return user


def reviewer_permission(name: str):
    def dependency(user: User = Depends(require_reviewer)) -> User:
        if not getattr(user, f"perm_{name}", False):
            labels = {"upload": "上传制度", "delete": "删除制度", "relation": "关系管理"}
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"当前账号没有{labels[name]}权限")
        return user

    return dependency

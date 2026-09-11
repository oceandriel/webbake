"""FastAPI 公共依赖：分页参数、后台 JWT 认证、外部 API Token 认证。"""

from __future__ import annotations

import secrets

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import database
from app.config import settings
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
api_key_scheme = APIKeyHeader(name="X-API-Token", auto_error=False)


def get_db():
    # 直接转发 database.get_db，保持会话来源唯一
    yield from database.get_db()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_api_token(api_key: str | None = Depends(api_key_scheme)) -> str:
    """外部集成 API：Token 直接来自环境变量 API_TOKEN，无 UI 管理。"""
    if not api_key or not secrets.compare_digest(api_key, settings.api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或缺失的 API Token（请通过请求头 X-API-Token 传入）",
            headers={"WWW-Authenticate": "ApiToken"},
        )
    return api_key


class Pagination:
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
    ):
        self.page = max(page, 1)
        self.page_size = min(max(page_size, 1), 200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

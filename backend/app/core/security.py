"""管理台会话：密码校验、JWT 签发与请求依赖。"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings

_ALGORITHM = "HS256"
_SALT = secrets.token_bytes(16)
_PASSWORD_HASH = hashlib.scrypt(settings.admin_password.encode("utf-8"), salt=_SALT, n=2**14, r=8, p=1)


def verify_password(password: str) -> bool:
    candidate = hashlib.scrypt(password.encode("utf-8"), salt=_SALT, n=2**14, r=8, p=1)
    return hmac.compare_digest(candidate, _PASSWORD_HASH)


def verify_credentials(username: str, password: str) -> bool:
    user_ok = hmac.compare_digest(username, settings.admin_username)
    return verify_password(password) and user_ok


def create_token() -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": settings.admin_username,
        "iat": now,
        "exp": now + timedelta(hours=settings.admin_session_hours),
        "iss": "startools-admin",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM], issuer="startools-admin")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录") from exc


async def require_admin(request: Request) -> str:
    token = request.cookies.get(settings.admin_cookie_name)
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录管理台")
    payload = decode_token(token)
    return str(payload.get("sub", settings.admin_username))


AdminUser = Depends(require_admin)

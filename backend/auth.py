from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from .config import settings

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def create_token(subject: str, role: str, customer_id: str | None = None) -> str:
    payload = {"sub": subject, "role": role, "customer_id": customer_id,
               "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> dict:
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        return jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


def require_role(role: str):
    def dependency(user: Annotated[dict, Depends(current_user)]) -> dict:
        if user.get("role") != role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return dependency


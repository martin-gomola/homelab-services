from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import SETTINGS

security = HTTPBearer(auto_error=False)


def validate_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    if not SETTINGS.bridge_api_key:
        return
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    if credentials.credentials != SETTINGS.bridge_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )


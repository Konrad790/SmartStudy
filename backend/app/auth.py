import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)
_jwks_client: PyJWKClient | None = None


def _jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.clerk_jwks_url)
    return _jwks_client


def _decode_clerk_token(token: str) -> dict:
    try:
        signing_key = _jwks().get_signing_key_from_jwt(token)
        kwargs: dict = {}
        if settings.clerk_issuer:
            kwargs["issuer"] = settings.clerk_issuer.rstrip("/")
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            **kwargs,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload = _decode_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")
    if not clerk_id or not isinstance(clerk_id, str):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    email = payload.get("email")
    if isinstance(email, str):
        email = email.lower()
    else:
        email = f"{clerk_id}@users.clerk"

    result = await db.execute(select(User).where(User.clerkId == clerk_id))
    user = result.scalar_one_or_none()
    if user:
        if user.email != email and "@" in email:
            user.email = email
            await db.commit()
        return user

    result = await db.execute(select(User).where(User.email == email))
    legacy = result.scalar_one_or_none()
    if legacy and legacy.clerkId is None:
        legacy.clerkId = clerk_id
        await db.commit()
        await db.refresh(legacy)
        return legacy

    user = User(id=str(uuid.uuid4()), email=email, passwordHash="", clerkId=clerk_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

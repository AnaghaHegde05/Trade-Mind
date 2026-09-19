from fastapi import Header, HTTPException, status
from typing import Optional
from backend.config.settings import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias=settings.API_KEY_HEADER)):
    """
    Shared-secret check for write endpoints (/analyze, /datasets/upload).

    If TRADE_API_KEY is not set in the environment, settings.API_KEY is
    empty and auth is treated as not configured - requests pass through
    unauthenticated, so local development and demo runs stay frictionless.
    Setting TRADE_API_KEY turns on real enforcement: every request to a
    protected route must then send a matching X-API-Key header.
    """
    if not settings.API_KEY:
        return

    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key."
        )

"""Authentication dependencies."""

import os
from typing import Optional

from fastapi import Header, HTTPException, status
from pydantic import SecretStr

# Allow setting API key via env var. 
# SECURITY: Do not hardcode production keys here. Set DASHBOARD_API_KEY in your .env or system environment.
API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-key-placeholder")


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Verify API key from header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        # For development convenience, if no key provided, maybe allow?
        # Better to enforce it to match frontend behavior.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key

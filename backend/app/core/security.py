import httpx
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> dict:
    """
    Dependency to validate the Supabase access token (JWT) passed in the Bearer header.
    Bypasses and injects a mock demo user if DEMO_MODE is enabled for local testing.
    """
    if settings.DEMO_MODE:
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "demo@local.dev",
            "role": "user"
        }

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    token = credentials.credentials
    url = settings.SUPABASE_URL.strip()
    
    # Normalize URL to project root (removing /rest/v1/)
    if url.endswith("/rest/v1/"):
        url = url[:-9]
    elif url.endswith("/rest/v1"):
        url = url[:-8]
    if url.endswith("/"):
        url = url[:-1]
        
    auth_url = f"{url}/auth/v1/user"
    
    # Supabase expects the anon/service key in the apikey header, and JWT in Authorization
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(auth_url, headers=headers, timeout=5.0)
            if response.status_code != 200:
                logger.warning(f"[AUTH FAILURE] Token validation rejected by Supabase (status code: {response.status_code})")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token."
                )
            
            user_data = response.json()
            # Return parsed user details (id, email)
            return {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "role": user_data.get("role")
            }
        except httpx.RequestError as e:
            logger.error(f"[AUTH ERROR] Failed to connect to Supabase Auth API: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication server is currently unreachable."
            )

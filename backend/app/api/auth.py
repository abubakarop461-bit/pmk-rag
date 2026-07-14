from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.schemas.auth import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns user identity details extracted and validated from the active JWT token.
    """
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user.get("role", "user")
    )

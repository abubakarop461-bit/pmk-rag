from typing import Optional
from pydantic import BaseModel, EmailStr

class UserProfile(BaseModel):
    id: str
    email: EmailStr
    role: Optional[str] = "user"

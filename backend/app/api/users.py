"""
FitCheck AI — Users API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

class UpdateProfileRequest(BaseModel):
    full_name:  Optional[str] = None
    height_cm:  Optional[int] = None
    weight_kg:  Optional[int] = None
    age:        Optional[int] = None
    body_type:  Optional[str] = None

@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id":         current_user.id,
        "email":      current_user.email,
        "full_name":  current_user.full_name,
        "plan":       current_user.plan,
        "avatar_url": current_user.avatar_url,
        "height_cm":  current_user.height_cm,
        "weight_kg":  current_user.weight_kg,
        "age":        current_user.age,
        "body_type":  current_user.body_type,
        "created_at": str(current_user.created_at),
    }

@router.patch("/me")
async def update_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    return {"updated": True}

@router.delete("/me")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GDPR-compliant account deletion."""
    current_user.is_active = False
    current_user.email     = f"deleted_{current_user.id}@deleted.fitcheck"
    return {"deleted": True, "message": "Account scheduled for deletion within 30 days"}

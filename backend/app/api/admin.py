"""FitCheck AI — Admin API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User, UserStatus, UserPlan
from app.models.tryon import TryOn, TryOnStatus

router = APIRouter()

@router.get("/stats")
async def platform_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    total_users  = (await db.execute(select(func.count(User.id)))).scalar()
    total_tryons = (await db.execute(select(func.count(TryOn.id)))).scalar()
    pro_users    = (await db.execute(select(func.count(User.id)).where(User.plan == UserPlan.PRO))).scalar()
    biz_users    = (await db.execute(select(func.count(User.id)).where(User.plan == UserPlan.BUSINESS))).scalar()
    avg_render   = (await db.execute(select(func.avg(TryOn.render_time_ms)).where(TryOn.status == TryOnStatus.COMPLETED))).scalar()

    return {
        "total_users":    total_users,
        "total_tryons":   total_tryons,
        "pro_users":      pro_users,
        "business_users": biz_users,
        "avg_render_ms":  round(avg_render or 0, 0),
    }

@router.get("/users")
async def list_users(
    page: int = 1, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
    )
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "plan": u.plan, "status": u.status, "created_at": str(u.created_at)} for u in users]

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status    = UserStatus.BANNED
    user.is_active = False
    return {"banned": True}

@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.status    = UserStatus.ACTIVE
    user.is_active = True
    return {"unbanned": True}

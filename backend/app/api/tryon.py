"""
FitCheck AI — Try-On API
Smart routing: free (HuggingFace) vs paid (Replicate via credits)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.core.rate_limiter import (
    check_tryon_limit, increment_tryon_count,
    get_tryon_usage, check_guest_ip_limit
)
from app.models.user import User, UserPlan
from app.models.tryon import TryOn, TryOnStatus, ProductType
from app.services.ai_service import run_tryon
from app.services.storage_service import upload_image, validate_image
from app.services.product_service import scrape_product
from app.api.credits import deduct_credit

router = APIRouter()
logger = logging.getLogger("fitcheck.tryon")


class TryOnResponse(BaseModel):
    id:               str
    status:           str
    engine:           Optional[str]   # "huggingface" | "replicate" | "mock"
    result_front_url: Optional[str]
    product_name:     Optional[str]   # Product name for display
    product_type:     Optional[str]   # Product category
    person_details:   Optional[dict]  # {height_cm, weight_kg, body_type, age}
    fit_score:        Optional[float]
    recommended_size: Optional[str]
    ai_notes:         Optional[str]
    render_time_ms:   Optional[int]
    credits_used:     int
    created_at:       str


# ── POST /tryon ───────────────────────────────────────
@router.post("/", response_model=TryOnResponse)
async def create_tryon(
    request:       Request,
    background_tasks: BackgroundTasks,
    person_image:  UploadFile = File(...),
    product_image: UploadFile = File(None),
    product_url:   str = Form(None),
    product_type:  str = Form("clothing"),
    height_cm:     int = Form(None),
    weight_kg:     int = Form(None),
    age:           int = Form(None),
    body_type:     str = Form(None),
    use_credits:   bool = Form(False),  # frontend sends True when user chooses paid
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    # ── 1. Decide routing ────────────────────────────
    using_credits = False

    if current_user and use_credits:
        # User wants to use a credit — check balance
        if current_user.credits < 1:
            raise HTTPException(402, {
                "error":   "insufficient_credits",
                "message": "You don't have enough credits. Buy a pack to continue.",
                "balance": current_user.credits,
            })
        using_credits = True
    else:
        # Free path — check daily limit
        if current_user:
            await check_tryon_limit(current_user.id, current_user.plan, request)
        else:
            await check_guest_ip_limit(request)

    # ── 2. Validate + upload person photo ────────────
    person_bytes = await person_image.read()
    await validate_image(person_bytes, person_image.content_type)
    person_s3_url = await upload_image(person_bytes, folder="persons")

    # ── 3. Get product image ──────────────────────────
    product_name = None
    if product_image and product_image.filename:
        product_bytes = await product_image.read()
        await validate_image(product_bytes, product_image.content_type)
        product_s3_url = await upload_image(product_bytes, folder="products")
    elif product_url:
        scraped = await scrape_product(product_url)
        if not scraped:
            raise HTTPException(400, "Could not extract product from URL. Upload the image directly.")
        product_bytes  = scraped.get("image_bytes")
        product_name   = scraped.get("name")
        product_s3_url = await upload_image(product_bytes, folder="products")
    else:
        raise HTTPException(400, "Provide either product_image or product_url")

    # ── 4. Deduct credit BEFORE running AI ───────────
    if using_credits:
        deducted = await deduct_credit(db, current_user, "pending")
        if not deducted:
            raise HTTPException(402, "Credit deduction failed")

    # ── 5. Create DB record ───────────────────────────
    tryon = TryOn(
        user_id           = current_user.id if current_user else None,
        person_image_url  = person_s3_url,
        product_image_url = product_s3_url,
        product_type      = product_type,
        product_name      = product_name,
        product_url       = product_url,
        height_cm         = height_cm or (current_user.height_cm if current_user else None),
        weight_kg         = weight_kg or (current_user.weight_kg if current_user else None),
        age               = age,
        body_type         = body_type or (current_user.body_type if current_user else None),
        status            = TryOnStatus.PROCESSING,
    )
    db.add(tryon)
    await db.flush()
    tryon_id = tryon.id

    # ── 6. Run AI in background ───────────────────────
    background_tasks.add_task(
        _process_tryon,
        tryon_id, person_s3_url, product_s3_url,
        product_type, height_cm, weight_kg, body_type,
        current_user.id if current_user else None,
        using_credits,
    )

    return TryOnResponse(
        id=tryon_id, status="processing",
        engine="replicate" if using_credits else "huggingface",
        product_name=product_name,
        product_type=product_type,
        person_details={
            "height_cm": height_cm or (current_user.height_cm if current_user else None),
            "weight_kg": weight_kg or (current_user.weight_kg if current_user else None),
            "body_type": body_type or (current_user.body_type if current_user else None),
            "age": age or (current_user.age if current_user else None),
        },
        result_front_url=None, fit_score=None,
        recommended_size=None, ai_notes=None, render_time_ms=None,
        credits_used=1 if using_credits else 0,
        created_at=str(datetime.now()),
    )


# ── GET /tryon/{id} — poll result ────────────────────
@router.get("/{tryon_id}", response_model=TryOnResponse)
async def get_tryon(
    tryon_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    result = await db.execute(select(TryOn).where(TryOn.id == tryon_id))
    tryon  = result.scalar_one_or_none()
    if not tryon:
        raise HTTPException(404, "Try-on not found")

    return TryOnResponse(
        id=tryon.id, status=tryon.status,
        engine=tryon.ai_engine,
        product_name=tryon.product_name,
        product_type=tryon.product_type,
        person_details={
            "height_cm": tryon.height_cm,
            "weight_kg": tryon.weight_kg,
            "body_type": tryon.body_type,
            "age": tryon.age,
        },
        result_front_url=tryon.result_front_url,
        fit_score=tryon.fit_score,
        recommended_size=tryon.recommended_size,
        ai_notes=tryon.ai_notes,
        render_time_ms=tryon.render_time_ms,
        credits_used=tryon.credits_used or 0,
        created_at=str(tryon.created_at),
    )


# ── POST /tryon/{id}/save ─────────────────────────────
@router.post("/{tryon_id}/save")
async def save_tryon(
    tryon_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TryOn).where(TryOn.id == tryon_id, TryOn.user_id == current_user.id)
    )
    tryon = result.scalar_one_or_none()
    if not tryon:
        raise HTTPException(404, "Try-on not found")
    tryon.is_saved = True
    return {"saved": True}


# ── GET /tryon/history/me ─────────────────────────────
@router.get("/history/me")
async def my_history(
    page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(TryOn).where(TryOn.user_id == current_user.id)
        .order_by(desc(TryOn.created_at)).offset(offset).limit(limit)
    )
    tryons = result.scalars().all()
    total  = (await db.execute(
        select(sqlfunc.count(TryOn.id)).where(TryOn.user_id == current_user.id)
    )).scalar()
    return {"items": [_dict(t) for t in tryons], "total": total, "page": page}


# ── GET /tryon/saved/me ───────────────────────────────
@router.get("/saved/me")
async def my_saved(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TryOn).where(TryOn.user_id == current_user.id, TryOn.is_saved == True)
        .order_by(desc(TryOn.created_at))
    )
    return [_dict(t) for t in result.scalars().all()]


# ── GET /tryon/usage/me ───────────────────────────────
@router.get("/usage/me")
async def my_usage(
    current_user: User = Depends(get_current_user),
):
    from app.core.rate_limiter import get_tryon_usage
    usage = await get_tryon_usage(current_user.id)
    return {
        **usage,
        "credits":  current_user.credits,
        "plan":     current_user.plan,
    }


# ── Background: run AI ────────────────────────────────
async def _process_tryon(
    tryon_id, person_url, product_url,
    product_type, height_cm, weight_kg, body_type,
    user_id, using_credits,
):
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            result = await run_tryon(
                person_url, product_url, product_type,
                height_cm, weight_kg, body_type,
                use_credits=using_credits,
            )

            r     = await db.execute(select(TryOn).where(TryOn.id == tryon_id))
            tryon = r.scalar_one_or_none()
            if tryon:
                tryon.status           = TryOnStatus.COMPLETED
                tryon.result_front_url = result.result_url
                tryon.fit_score        = result.fit_score
                tryon.recommended_size = result.recommended_size
                tryon.render_time_ms   = result.render_time_ms
                tryon.ai_notes         = result.ai_notes
                tryon.ai_engine        = result.engine
                tryon.credits_used     = 1 if using_credits else 0
                tryon.completed_at     = datetime.now(timezone.utc)
                await db.commit()

            if user_id and not using_credits:
                await increment_tryon_count(user_id)

            logger.info(f"Try-on {tryon_id} done via {result.engine} in {result.render_time_ms}ms")

        except Exception as e:
            logger.error(f"Try-on {tryon_id} failed: {e}")
            r     = await db.execute(select(TryOn).where(TryOn.id == tryon_id))
            tryon = r.scalar_one_or_none()
            if tryon:
                tryon.status        = TryOnStatus.FAILED
                tryon.error_message = str(e)
                await db.commit()


def _dict(t: TryOn) -> dict:
    return {
        "id": t.id, "status": t.status,
        "product_name": t.product_name, "product_type": t.product_type,
        "result_front_url": t.result_front_url,
        "fit_score": t.fit_score, "recommended_size": t.recommended_size,
        "credits_used": t.credits_used or 0,
        "is_saved": t.is_saved, "created_at": str(t.created_at),
    }

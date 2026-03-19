"""
FitCheck AI — Credits API
Buy credits, check balance, transaction history, Razorpay webhook
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional
import hmac, hashlib, json, logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserPlan, CreditTransaction
from app.core.config import settings

router  = APIRouter()
logger  = logging.getLogger("fitcheck.credits")

# ── Credit packs (₹ → credits) ────────────────────────
CREDIT_PACKS = {
    "starter":   {"credits": 8,  "price_inr": 99,  "label": "Starter Pack"},
    "popular":   {"credits": 20, "price_inr": 199, "label": "Popular Pack"},
    "value":     {"credits": 50, "price_inr": 449, "label": "Value Pack"},
}
# 1 credit = 1 try-on on Replicate (best quality)
CREDITS_PER_TRYON = 1


# ── Schemas ───────────────────────────────────────────
class CreateOrderRequest(BaseModel):
    pack_id: str   # "starter" | "popular" | "value"

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id:   str
    razorpay_payment_id: str
    razorpay_signature:  str
    pack_id:             str


# ── GET /credits/packs — list available packs ─────────
@router.get("/packs")
async def list_packs():
    return [
        {
            "id":          k,
            "credits":     v["credits"],
            "price_inr":   v["price_inr"],
            "label":       v["label"],
            "per_tryon":   round(v["price_inr"] / v["credits"], 1),
        }
        for k, v in CREDIT_PACKS.items()
    ]


# ── GET /credits/balance — my balance ────────────────
@router.get("/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    return {
        "credits":               current_user.credits,
        "total_credits_purchased": current_user.total_credits_purchased,
        "total_tryons":          current_user.total_tryons,
        "plan":                  current_user.plan,
    }


# ── POST /credits/order — create Razorpay order ──────
@router.post("/order")
async def create_order(
    data: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """Creates a Razorpay order for the selected credit pack."""
    pack = CREDIT_PACKS.get(data.pack_id)
    if not pack:
        raise HTTPException(400, f"Invalid pack. Choose from: {list(CREDIT_PACKS.keys())}")

    if not settings.RAZORPAY_KEY_ID:
        # Dev mode — return mock order
        return {
            "order_id":    f"order_mock_{int(__import__('time').time())}",
            "amount":      pack["price_inr"] * 100,   # Razorpay uses paise
            "currency":    "INR",
            "key_id":      "rzp_test_mock",
            "pack":        pack,
            "user_email":  current_user.email,
            "user_name":   current_user.full_name or "",
            "mock":        True,
        }

    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        order = client.order.create({
            "amount":   pack["price_inr"] * 100,
            "currency": "INR",
            "notes": {
                "user_id": current_user.id,
                "pack_id": data.pack_id,
                "credits": pack["credits"],
            }
        })
        return {
            "order_id":   order["id"],
            "amount":     order["amount"],
            "currency":   order["currency"],
            "key_id":     settings.RAZORPAY_KEY_ID,
            "pack":       pack,
            "user_email": current_user.email,
            "user_name":  current_user.full_name or "",
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(500, "Payment order creation failed")


# ── POST /credits/verify — verify payment & add credits
@router.post("/verify")
async def verify_payment(
    data: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verifies Razorpay payment signature then adds credits to user account.
    This is the secure server-side check — never trust frontend alone.
    """
    pack = CREDIT_PACKS.get(data.pack_id)
    if not pack:
        raise HTTPException(400, "Invalid pack")

    # Dev mode mock — auto-approve
    if not settings.RAZORPAY_KEY_SECRET or data.razorpay_order_id.startswith("order_mock"):
        return await _add_credits(
            db, current_user, pack["credits"], pack["price_inr"],
            data.razorpay_payment_id or "mock_payment", data.pack_id
        )

    # Verify Razorpay signature
    body = f"{data.razorpay_order_id}|{data.razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, data.razorpay_signature):
        logger.warning(f"Invalid payment signature for user {current_user.id}")
        raise HTTPException(400, "Invalid payment signature")

    return await _add_credits(
        db, current_user, pack["credits"], pack["price_inr"],
        data.razorpay_payment_id, data.pack_id
    )


# ── POST /credits/webhook — Razorpay webhook ─────────
@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: Optional[str] = Header(None),
):
    body = await request.body()

    # Verify webhook signature
    if x_razorpay_signature and settings.RAZORPAY_KEY_SECRET:
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(400, "Invalid webhook signature")

    event = json.loads(body)
    logger.info(f"Razorpay webhook: {event.get('event')}")

    # payment.captured = money received successfully
    if event.get("event") == "payment.captured":
        payment = event.get("payload", {}).get("payment", {}).get("entity", {})
        notes   = payment.get("notes", {})
        user_id = notes.get("user_id")
        pack_id = notes.get("pack_id")

        if user_id and pack_id and pack_id in CREDIT_PACKS:
            pack = CREDIT_PACKS[pack_id]
            result = await db.execute(select(User).where(User.id == user_id))
            user   = result.scalar_one_or_none()
            if user:
                await _add_credits(
                    db, user, pack["credits"], pack["price_inr"],
                    payment.get("id"), pack_id
                )

    return {"received": True}


# ── GET /credits/history ──────────────────────────────
@router.get("/history")
async def credit_history(
    page: int = 1, limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(desc(CreditTransaction.created_at))
        .offset(offset).limit(limit)
    )
    txns = result.scalars().all()
    return [
        {
            "id":             t.id,
            "type":           t.type,
            "credits":        t.credits,
            "balance_after":  t.balance_after,
            "description":    t.description,
            "amount_inr":     t.amount_inr,
            "created_at":     str(t.created_at),
        }
        for t in txns
    ]


# ── Internal: add credits to account ─────────────────
async def _add_credits(db, user: User, credits: int, price_inr: float,
                        payment_id: str, pack_id: str):
    user.credits                 += credits
    user.total_credits_purchased += credits
    if user.credits > 0:
        user.plan = UserPlan.CREDITED

    txn = CreditTransaction(
        user_id             = user.id,
        type                = "purchase",
        credits             = credits,
        balance_after       = user.credits,
        description         = f"Bought {CREDIT_PACKS[pack_id]['label']} ({credits} credits)",
        razorpay_payment_id = payment_id,
        amount_inr          = price_inr,
    )
    db.add(txn)
    await db.commit()

    logger.info(f"Added {credits} credits to user {user.id} | balance={user.credits}")
    return {
        "success":      True,
        "credits_added": credits,
        "new_balance":  user.credits,
        "message":      f"✓ {credits} credits added to your account!",
    }


# ── Internal: deduct 1 credit for try-on ─────────────
async def deduct_credit(db, user: User, tryon_id: str) -> bool:
    """Returns True if credit deducted, False if insufficient."""
    if user.credits < CREDITS_PER_TRYON:
        return False

    user.credits      -= CREDITS_PER_TRYON
    user.total_tryons += 1
    if user.credits == 0:
        user.plan = UserPlan.FREE

    txn = CreditTransaction(
        user_id       = user.id,
        type          = "spend",
        credits       = -CREDITS_PER_TRYON,
        balance_after = user.credits,
        description   = f"Try-on #{tryon_id[:8]}",
    )
    db.add(txn)
    return True

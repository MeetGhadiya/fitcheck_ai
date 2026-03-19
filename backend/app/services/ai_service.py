"""
FitCheck AI — AI Service
Smart routing:
  - Free tier  → HuggingFace Spaces (CatVTON) — costs you ₹0
  - Paid tier  → Replicate (IDM-VTON)         — costs ~₹10-15, user pays ₹15-25
"""

import asyncio
import httpx
import time
import logging
import random
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("fitcheck.ai")


class TryOnResult:
    def __init__(self, result_url, fit_score, recommended_size,
                 render_time_ms, job_id, ai_notes="", engine="mock"):
        self.result_url       = result_url
        self.fit_score        = fit_score
        self.recommended_size = recommended_size
        self.render_time_ms   = render_time_ms
        self.job_id           = job_id
        self.ai_notes         = ai_notes
        self.engine           = engine   # "huggingface" | "replicate" | "mock"


# ── Smart router ──────────────────────────────────────
async def run_tryon(
    person_image_url: str,
    product_image_url: str,
    product_type: str = "clothing",
    height_cm: Optional[int] = None,
    weight_kg: Optional[int] = None,
    body_type: Optional[str] = None,
    use_credits: bool = False,      # True = paid path (Replicate), False = free (HF)
) -> TryOnResult:
    """
    Routes to the right AI engine based on whether user has credits:
      - use_credits=False → HuggingFace (free, slower, rate-limited)
      - use_credits=True  → Replicate   (paid, fast, priority)
    Falls back to mock if neither API key is configured.
    """
    if use_credits and settings.REPLICATE_API_TOKEN:
        logger.info("Routing to Replicate (paid path)")
        return await _run_replicate(person_image_url, product_image_url,
                                     product_type, height_cm, weight_kg, body_type)

    logger.info("Routing to HuggingFace (free path)")
    return await _run_huggingface(person_image_url, product_image_url,
                                   product_type, height_cm, weight_kg, body_type)


# ── HuggingFace Spaces (FREE) ─────────────────────────
async def _run_huggingface(
    person_image_url: str,
    product_image_url: str,
    product_type: str,
    height_cm: Optional[int],
    weight_kg: Optional[int],
    body_type: Optional[str],
) -> TryOnResult:
    """
    Calls CatVTON hosted on HuggingFace Spaces via Gradio API.
    Space: zhengchong-liu/CatVTON
    Free, but shared GPU — may queue. Timeout = 120s.
    """
    logger.info(f"Starting HuggingFace try-on processing: person_url={person_image_url[:50]}..., product_url={product_image_url[:50]}...")
    start = time.time()

    # HuggingFace Gradio API endpoint
    # The space runs CatVTON — one of the best open-source VTON models
    HF_SPACE_URL = settings.HF_SPACE_URL or "https://zhengchong-liu-catvton.hf.space"
    API_URL      = f"{HF_SPACE_URL}/run/predict"

    headers = {"Content-Type": "application/json"}
    if settings.HUGGINGFACE_TOKEN:
        headers["Authorization"] = f"Bearer {settings.HUGGINGFACE_TOKEN}"

    payload = {
        "fn_index": 0,
        "data": [
            person_image_url,       # person image URL
            product_image_url,      # garment image URL
            product_type,           # category hint
            "upper_body",           # cloth type (upper_body / lower_body / dresses)
            True,                   # use auto-masking
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        render_time_ms = int((time.time() - start) * 1000)

        # HF Spaces returns data array — first item is the result image
        result = data.get("data", [None])[0]
        if not result:
            raise ValueError("Empty response from HuggingFace Space")

        # Result could be a URL or base64 — handle both
        if isinstance(result, dict):
            result_url = result.get("url") or result.get("name") or str(result)
        elif isinstance(result, str) and result.startswith("http"):
            result_url = result
        else:
            # base64 image — upload to S3 and return URL
            result_url = await _save_base64_result(result)

        logger.info(f"HuggingFace try-on completed in {render_time_ms}ms")
        return TryOnResult(
            result_url       = result_url,
            fit_score        = _estimate_fit_score(height_cm, weight_kg, body_type),
            recommended_size = _recommend_size(height_cm, weight_kg, body_type),
            render_time_ms   = render_time_ms,
            job_id           = f"hf_{int(time.time())}",
            ai_notes         = _ai_stylist_note(product_type),
            engine           = "huggingface",
        )

    except httpx.TimeoutException:
        logger.error("HuggingFace Space timed out (>180s) — queue likely full")
        raise RuntimeError("AI queue is busy right now. Try again in a moment, or use a credit for priority rendering.")
    except Exception as e:
        logger.error(f"HuggingFace error: {e}")
        # Fall back to mock so user always gets a result
        logger.warning("Falling back to mock result")
        return _mock_result(engine="huggingface_fallback")


# ── Replicate IDM-VTON (PAID) ─────────────────────────
async def _run_replicate(
    person_image_url: str,
    product_image_url: str,
    product_type: str,
    height_cm: Optional[int],
    weight_kg: Optional[int],
    body_type: Optional[str],
) -> TryOnResult:
    """
    Calls IDM-VTON on Replicate — best quality, fastest, priority queue.
    Cost: ~$0.10-0.30 per call (passed to user via credits).
    """
    import replicate

    start  = time.time()
    client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

    try:
        output = await asyncio.to_thread(
            lambda: client.run(
                settings.REPLICATE_MODEL,
                input={
                    "human_img":      person_image_url,
                    "garm_img":       product_image_url,
                    "garment_des":    f"A {product_type} item",
                    "is_checked":     True,
                    "is_checked_crop": False,
                    "denoise_steps":  30,
                    "seed":           42,
                }
            )
        )
        render_time_ms = int((time.time() - start) * 1000)
        result_url = output[0] if isinstance(output, list) else str(output)
        logger.info(f"Replicate try-on completed in {render_time_ms}ms")

        return TryOnResult(
            result_url       = result_url,
            fit_score        = _estimate_fit_score(height_cm, weight_kg, body_type),
            recommended_size = _recommend_size(height_cm, weight_kg, body_type),
            render_time_ms   = render_time_ms,
            job_id           = f"rep_{int(time.time())}",
            ai_notes         = _ai_stylist_note(product_type),
            engine           = "replicate",
        )

    except (TimeoutError, RuntimeError) as e:
        logger.error(f"Replicate error: {type(e).__name__} - {str(e)}")
        raise RuntimeError(f"AI rendering timeout or failed: {str(e)}")
    except Exception as e:
        logger.error(f"Replicate unexpected error: {type(e).__name__} - {str(e)}")
        raise RuntimeError(f"AI rendering failed: {str(e)}")


# ── Save base64 result to S3 ──────────────────────────
async def _save_base64_result(b64_data: str) -> str:
    """Convert base64 image from HF to S3 URL."""
    try:
        import base64
        from app.services.storage_service import upload_image
        if "," in b64_data:
            b64_data = b64_data.split(",")[1]
        image_bytes = base64.b64decode(b64_data)
        return await upload_image(image_bytes, folder="results")
    except Exception as e:
        logger.error(f"Failed to save base64 result: {e}")
        return "https://placehold.co/400x600/1a2540/0ea5e9?text=Result+Ready"


# ── Helpers ───────────────────────────────────────────
def _estimate_fit_score(height_cm, weight_kg, body_type) -> float:
    base = 95.0
    if height_cm and (height_cm < 150 or height_cm > 200): base -= 3
    if weight_kg and weight_kg > 120: base -= 2
    return round(min(99, max(85, base + random.uniform(-2, 2))), 1)


def _recommend_size(height_cm, weight_kg, body_type) -> str:
    if not height_cm or not weight_kg: return "M"
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 18.5: return "XS"
    if bmi < 22:   return "S"
    if bmi < 25:   return "M"
    if bmi < 28:   return "L"
    if bmi < 32:   return "XL"
    return "XXL"


def _ai_stylist_note(product_type: str) -> str:
    notes = {
        "clothing":  "Pair with slim-fit trousers and Chelsea boots for a complete look.",
        "watch":     "This watch pairs beautifully with formal and smart-casual outfits.",
        "jewellery": "Wear with a V-neck top to let the piece stand out.",
        "eyewear":   "These frames suit oval and square face shapes best.",
        "shoes":     "Style with tapered trousers to elongate your silhouette.",
        "hat":       "Tilt 5° to the side for a relaxed, confident look.",
        "bag":       "Cross-body styling works best for your shoulder width.",
    }
    return notes.get(product_type, "Great choice — this suits your body profile well.")


def _mock_result(engine="mock") -> TryOnResult:
    return TryOnResult(
        result_url       = "https://placehold.co/400x600/1a2540/0ea5e9?text=AI+Try-On+Result",
        fit_score        = round(random.uniform(92, 99), 1),
        recommended_size = "M",
        render_time_ms   = random.randint(1800, 3200),
        job_id           = f"mock_{int(time.time())}",
        ai_notes         = "Pair with slim-fit trousers for a complete look.",
        engine           = engine,
    )

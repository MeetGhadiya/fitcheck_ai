"""FitCheck AI — Configuration"""
from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    APP_NAME: str = "FitCheck AI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production-set-in-env"  # MUST be configured in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/fitcheck"
    REDIS_URL: str = "redis://localhost:6379"

    ALLOWED_ORIGINS: List[str] = [
        # Development — All common localhost ports
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5500", "http://127.0.0.1:5500",
        "http://localhost:8080", "http://127.0.0.1:8080",
        # Production
        "https://fitcheck.ai", "https://www.fitcheck.ai",
    ]
    ALLOWED_HOSTS: List[str] = ["fitcheck.ai", "www.fitcheck.ai", "localhost"]

    # ── AI: HuggingFace (FREE) ────────────────────────
    HF_SPACE_URL: str = "https://zhengchong-liu-catvton.hf.space"
    HUGGINGFACE_TOKEN: str = ""     # optional — works without it, but may get queued faster with it

    # ── AI: Replicate (PAID) ──────────────────────────
    REPLICATE_API_TOKEN: str = ""
    REPLICATE_MODEL: str = "cuuupid/idm-vton:906425dbca90663ff5427624839572cc56ea7d380343d13e2a4c4b09d3f0c30f"

    # ── Storage: Cloudflare R2 ────────────────────────
    S3_BUCKET: str = "fitcheck-uploads"
    S3_REGION: str = "auto"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""

    # ── Email: Resend ─────────────────────────────────
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@fitcheck.ai"

    # ── Payments: Razorpay (for credit top-ups) ───────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Rate limits (free tier) ───────────────────────
    FREE_DAILY_TRYON_LIMIT: int = 3
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

"""
FitCheck AI — Storage Service
Upload images to S3 / Cloudflare R2 with validation
"""

import boto3
import uuid
import io
import logging
from fastapi import HTTPException
from PIL import Image as PILImage

from app.core.config import settings

logger = logging.getLogger("fitcheck.storage")


def _get_s3_client():
    kwargs = dict(
        region_name          = settings.S3_REGION,
        aws_access_key_id    = settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key= settings.AWS_SECRET_ACCESS_KEY,
    )
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL  # for Cloudflare R2
    return boto3.client("s3", **kwargs)


async def validate_image(image_bytes: bytes, content_type: str) -> None:
    """Validate image: type, size, dimensions."""
    # Size check
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            400,
            f"Image too large ({size_mb:.1f}MB). Max allowed: {settings.MAX_IMAGE_SIZE_MB}MB"
        )

    # Type check
    if content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            400,
            f"Invalid image type '{content_type}'. Allowed: {settings.ALLOWED_IMAGE_TYPES}"
        )

    # PIL validation (ensures it's a real image, not a malicious file)
    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise HTTPException(400, "Invalid or corrupted image file")

    # Minimum dimensions
    img = PILImage.open(io.BytesIO(image_bytes))
    w, h = img.size
    if w < 100 or h < 100:
        raise HTTPException(400, f"Image too small ({w}×{h}). Minimum 100×100px required.")


async def upload_image(image_bytes: bytes, folder: str = "uploads") -> str:
    """
    Upload image to S3/R2 and return public URL.
    Falls back to a placeholder URL if credentials not configured.
    """
    if not settings.AWS_ACCESS_KEY_ID:
        logger.warning("No S3 credentials — using placeholder URL")
        return f"https://placehold.co/600x800/1a2540/0ea5e9?text={folder}"

    filename = f"{folder}/{uuid.uuid4().hex}.jpg"

    # Convert to JPEG for consistency
    try:
        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90, optimize=True)
        buffer.seek(0)
        optimized_bytes = buffer.read()
    except Exception:
        optimized_bytes = image_bytes
        filename = filename.replace(".jpg", ".png")

    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket      = settings.S3_BUCKET,
            Key         = filename,
            Body        = optimized_bytes,
            ContentType = "image/jpeg",
            ACL         = "public-read",
        )

        if settings.S3_ENDPOINT_URL:
            # Cloudflare R2 public URL format
            return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET}/{filename}"
        else:
            # AWS S3
            return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{filename}"

    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(500, "Image upload failed. Please try again.")


async def delete_image(url: str) -> bool:
    """Delete an image from S3 by URL."""
    if not settings.AWS_ACCESS_KEY_ID:
        return True
    try:
        # Extract key from URL
        key = url.split(f"{settings.S3_BUCKET}/")[-1]
        s3 = _get_s3_client()
        s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except Exception as e:
        logger.error(f"S3 delete failed: {e}")
        return False

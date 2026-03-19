"""FitCheck AI — Products API"""
from fastapi import APIRouter, HTTPException
from app.services.product_service import scrape_product

router = APIRouter()

@router.get("/scrape")
async def scrape_product_url(url: str):
    """Scrape product details from a URL."""
    if not url.startswith("http"):
        raise HTTPException(400, "Invalid URL")
    result = await scrape_product(url)
    if not result:
        raise HTTPException(422, "Could not extract product from this URL")
    return {
        "name":      result.get("name"),
        "image_url": result.get("image_url"),
    }

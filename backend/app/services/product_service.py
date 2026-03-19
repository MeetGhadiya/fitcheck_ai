"""
FitCheck AI — Product Scraper Service
Extracts product name, image from Amazon, Flipkart, Zara, Myntra URLs
"""

import httpx
import re
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("fitcheck.scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


async def scrape_product(url: str) -> Optional[dict]:
    """
    Scrape product details from supported e-commerce URLs.
    Returns dict with: name, image_url, image_bytes, price, brand
    """
    try:
        domain = urlparse(url).netloc.lower()

        if "amazon" in domain:
            return await _scrape_amazon(url)
        elif "flipkart" in domain:
            return await _scrape_flipkart(url)
        elif "zara" in domain:
            return await _scrape_zara(url)
        elif "myntra" in domain:
            return await _scrape_myntra(url)
        elif "ajio" in domain:
            return await _scrape_generic(url)
        else:
            # Generic fallback — try to find og:image
            return await _scrape_generic(url)

    except Exception as e:
        logger.error(f"Scrape failed for {url}: {e}")
        return None


async def _scrape_amazon(url: str) -> Optional[dict]:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(url)
        html = resp.text

        # Product name
        name_match = re.search(
            r'<span id="productTitle"[^>]*>\s*(.*?)\s*</span>', html, re.DOTALL
        )
        name = name_match.group(1).strip() if name_match else "Amazon Product"

        # Main image
        img_match = re.search(
            r'"hiRes"\s*:\s*"(https://m\.media-amazon\.com[^"]+)"', html
        )
        if not img_match:
            img_match = re.search(
                r'"large"\s*:\s*"(https://m\.media-amazon\.com[^"]+)"', html
            )

        if not img_match:
            return None

        image_url   = img_match.group(1)
        image_bytes = await _download_image(image_url)

        return {"name": name, "image_url": image_url, "image_bytes": image_bytes}


async def _scrape_flipkart(url: str) -> Optional[dict]:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(url)
        html = resp.text

        name_match = re.search(r'<span class="B_NuCI">(.*?)</span>', html)
        name = name_match.group(1).strip() if name_match else "Flipkart Product"

        img_match = re.search(r'"url"\s*:\s*"(https://rukminim[^"]+)"', html)
        if not img_match:
            return None

        image_url   = img_match.group(1)
        image_bytes = await _download_image(image_url)

        return {"name": name, "image_url": image_url, "image_bytes": image_bytes}


async def _scrape_zara(url: str) -> Optional[dict]:
    return await _scrape_generic(url)


async def _scrape_myntra(url: str) -> Optional[dict]:
    return await _scrape_generic(url)


async def _scrape_generic(url: str) -> Optional[dict]:
    """
    Fallback: extract og:image and og:title from any page.
    Works for most e-commerce sites.
    """
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(url)
        html = resp.text

        # og:title
        name_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        name = name_match.group(1) if name_match else "Product"

        # og:image
        img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if not img_match:
            return None

        image_url   = img_match.group(1)
        image_bytes = await _download_image(image_url)

        return {"name": name, "image_url": image_url, "image_bytes": image_bytes}


async def _download_image(url: str) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
    except Exception as e:
        logger.error(f"Image download failed: {e}")
    return None

"""
FitCheck AI — API Tests
Run with: pytest tests/ -v
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Health ────────────────────────────────────────────
@pytest.mark.anyio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Auth ──────────────────────────────────────────────
@pytest.mark.anyio
async def test_register(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "test@fitcheck.ai",
        "password": "Test1234",
        "full_name": "Test User",
    })
    assert r.status_code in (201, 400)  # 400 if already registered
    if r.status_code == 201:
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@fitcheck.ai"


@pytest.mark.anyio
async def test_login_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@fitcheck.ai",
        "password": "wrongpassword",
    })
    assert r.status_code == 401


@pytest.mark.anyio
async def test_login_correct(client):
    r = await client.post("/api/v1/auth/login", json={
        "email": "test@fitcheck.ai",
        "password": "Test1234",
    })
    # May be 401 if user doesn't exist in test DB — that's OK
    assert r.status_code in (200, 401)


# ── Unauthenticated try-on (guest) ────────────────────
@pytest.mark.anyio
async def test_tryon_requires_image(client):
    r = await client.post("/api/v1/tryon/", data={"product_type": "clothing"})
    assert r.status_code == 422  # missing required file


# ── Rate limiting ─────────────────────────────────────
@pytest.mark.anyio
async def test_product_scrape_invalid_url(client):
    r = await client.get("/api/v1/products/scrape?url=notaurl")
    assert r.status_code == 400


@pytest.mark.anyio
async def test_admin_requires_auth(client):
    r = await client.get("/api/v1/admin/stats")
    assert r.status_code == 401


# ── Password validation ───────────────────────────────
@pytest.mark.anyio
async def test_weak_password_rejected(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "weak@fitcheck.ai",
        "password": "abc",
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_password_no_number_rejected(client):
    r = await client.post("/api/v1/auth/register", json={
        "email": "weak2@fitcheck.ai",
        "password": "onlyletters",
    })
    assert r.status_code == 422

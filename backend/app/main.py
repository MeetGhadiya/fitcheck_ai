"""FitCheck AI — FastAPI Backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, tryon, users, products, admin, credits

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("fitcheck")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FitCheck AI backend starting...")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("Backend shutting down")

app = FastAPI(
    title="FitCheck AI API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Configuration — Development allows all localhost, Production is restricted
if settings.DEBUG:
    # Development: Allow all localhost origins with credentials for testing
    cors_origins = settings.ALLOWED_ORIGINS + [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
else:
    # Production: Only allow configured origins
    cors_origins = settings.ALLOWED_ORIGINS

app.add_middleware(CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^http://localhost:\d+$" if settings.DEBUG else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router,     prefix="/api/v1/auth",     tags=["Auth"])
app.include_router(tryon.router,    prefix="/api/v1/tryon",    tags=["Try-On"])
app.include_router(users.router,    prefix="/api/v1/users",    tags=["Users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(admin.router,    prefix="/api/v1/admin",    tags=["Admin"])
app.include_router(credits.router,  prefix="/api/v1/credits",  tags=["Credits"])

# Mount static files directory for uploaded images
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "FitCheck AI API"}

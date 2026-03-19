"""FitCheck AI — FastAPI Backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

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

app.add_middleware(CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/v1/auth",     tags=["Auth"])
app.include_router(tryon.router,    prefix="/api/v1/tryon",    tags=["Try-On"])
app.include_router(users.router,    prefix="/api/v1/users",    tags=["Users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(admin.router,    prefix="/api/v1/admin",    tags=["Admin"])
app.include_router(credits.router,  prefix="/api/v1/credits",  tags=["Credits"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "FitCheck AI API"}

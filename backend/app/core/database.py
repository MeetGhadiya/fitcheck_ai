"""
FitCheck AI — Database
Async SQLAlchemy setup with PostgreSQL
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import logging

logger = logging.getLogger("fitcheck.db")

# ── Engine ────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ── Session factory ───────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Base model ────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency — get DB session ───────────────────────
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Init DB (create tables) ───────────────────────────
async def init_db():
    # Import all models so they register with Base
    from app.models import user, tryon, product  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

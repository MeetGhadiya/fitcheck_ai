"""
FitCheck AI — Product Model
Cached scraped product data
"""

from sqlalchemy import Column, String, Text, DateTime, Float
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Product(Base):
    __tablename__ = "products"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_url   = Column(Text, unique=True, nullable=False, index=True)
    name         = Column(String(500), nullable=True)
    brand        = Column(String(255), nullable=True)
    image_url    = Column(Text, nullable=True)          # primary product image
    image_s3_url = Column(Text, nullable=True)          # our cached copy in S3
    price        = Column(Float, nullable=True)
    currency     = Column(String(10), default="INR")
    category     = Column(String(100), nullable=True)
    description  = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

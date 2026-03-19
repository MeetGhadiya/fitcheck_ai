"""FitCheck AI — TryOn Model (updated with ai_engine + credits_used)"""
from sqlalchemy import Column, String, Float, DateTime, Enum, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum, uuid

class TryOnStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"

class ProductType(str, enum.Enum):
    CLOTHING  = "clothing"; WATCH    = "watch";   JEWELLERY = "jewellery"
    EYEWEAR   = "eyewear";  SHOES    = "shoes";   HAT       = "hat"
    BAG       = "bag";      OTHER    = "other"

class TryOn(Base):
    __tablename__ = "tryons"
    id                = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id           = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    person_image_url  = Column(Text, nullable=False)
    product_image_url = Column(Text, nullable=False)
    product_type      = Column(String(50), default="clothing")
    product_name      = Column(String(255), nullable=True)
    product_url       = Column(Text, nullable=True)
    height_cm         = Column(Integer, nullable=True)
    weight_kg         = Column(Integer, nullable=True)
    age               = Column(Integer, nullable=True)
    body_type         = Column(String(50), nullable=True)
    status            = Column(String(20), default="pending")
    ai_engine         = Column(String(30), nullable=True)   # huggingface | replicate | mock
    credits_used      = Column(Integer, default=0)          # 0=free, 1=paid credit
    render_time_ms    = Column(Integer, nullable=True)
    fit_score         = Column(Float, nullable=True)
    recommended_size  = Column(String(20), nullable=True)
    ai_notes          = Column(Text, nullable=True)
    result_front_url  = Column(Text, nullable=True)
    result_side_url   = Column(Text, nullable=True)
    result_back_url   = Column(Text, nullable=True)
    result_3q_url     = Column(Text, nullable=True)
    is_saved          = Column(Boolean, default=False)
    is_flagged        = Column(Boolean, default=False)
    error_message     = Column(Text, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    completed_at      = Column(DateTime(timezone=True), nullable=True)
    user              = relationship("User", back_populates="tryons")

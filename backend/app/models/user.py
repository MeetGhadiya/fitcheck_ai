"""
FitCheck AI — User Model
Now includes credit balance for pay-as-you-go system
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum, Integer, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
import uuid


class UserPlan(str, enum.Enum):
    FREE     = "free"
    CREDITED = "credited"   # has paid credits loaded


class UserStatus(str, enum.Enum):
    ACTIVE  = "active"
    BANNED  = "banned"
    PENDING = "pending"


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name       = Column(String(255), nullable=True)
    avatar_url      = Column(Text, nullable=True)

    # Plan & status
    plan            = Column(Enum(UserPlan),   default=UserPlan.FREE,     nullable=False)
    status          = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_active       = Column(Boolean, default=True)
    is_admin        = Column(Boolean, default=False)

    # Credit system
    credits                 = Column(Integer, default=0, nullable=False)
    total_credits_purchased = Column(Integer, default=0)
    total_tryons            = Column(Integer, default=0)

    # Body measurements
    height_cm  = Column(Integer, nullable=True)
    weight_kg  = Column(Integer, nullable=True)
    age        = Column(Integer, nullable=True)
    body_type  = Column(String(50), nullable=True)

    # OAuth
    google_id     = Column(String(255), nullable=True, unique=True)
    auth_provider = Column(String(50), default="email")

    # Timestamps
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tryons      = relationship("TryOn", back_populates="user", lazy="dynamic")
    credit_txns = relationship("CreditTransaction", back_populates="user", lazy="dynamic")


class CreditTransaction(Base):
    """Full audit trail of every credit purchase and spend."""
    __tablename__ = "credit_transactions"

    id                  = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id             = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type                = Column(String(20), nullable=False)   # purchase | spend | refund
    credits             = Column(Integer,  nullable=False)     # +ve = added, -ve = spent
    balance_after       = Column(Integer,  nullable=False)
    description         = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    amount_inr          = Column(Float,    nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="credit_txns")

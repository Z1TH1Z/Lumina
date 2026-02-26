"""Transaction model for financial records."""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SAEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TransactionCategory(str, enum.Enum):
    HOUSING = "housing"
    FOOD = "food"
    TRANSPORT = "transport"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    SHOPPING = "shopping"
    INCOME = "income"
    TRANSFER = "transfer"
    INVESTMENT = "investment"
    INSURANCE = "insurance"
    EDUCATION = "education"
    OTHER = "other"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    # Core fields
    date = Column(Date, index=True)
    description = Column(String, index=True)
    merchant = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # Categorization
    category = Column(String(50), default=TransactionCategory.OTHER.value)
    category_confidence = Column(Float, nullable=True)
    user_corrected_category = Column(String(50), nullable=True)

    # Anomaly detection
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    anomaly_explanation = Column(Text, nullable=True)
    anomaly_confirmed = Column(Boolean, nullable=True)

    # Metadata
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="transactions")
    document = relationship("Document", back_populates="transactions")

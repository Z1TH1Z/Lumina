"""Document model for uploaded financial documents."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    BANK_STATEMENT = "bank_statement"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    TAX_DOCUMENT = "tax_document"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    doc_type = Column(String(50), default=DocumentType.OTHER.value)
    status = Column(String(50), default=DocumentStatus.PENDING.value)

    # Extracted content
    raw_text = Column(Text, nullable=True)
    parsed_data = Column(Text, nullable=True)  # JSON string of extracted data
    page_count = Column(Integer, nullable=True)
    transaction_count = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    transactions = relationship("Transaction", back_populates="document", cascade="all, delete-orphan")

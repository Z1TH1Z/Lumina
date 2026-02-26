"""Immutable audit log for compliance-ready logging."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Action tracking
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)

    # LLM interaction details
    user_input = Column(Text, nullable=True)
    rag_chunks_used = Column(Text, nullable=True)  # JSON array
    prompt_version = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    temperature = Column(Float, nullable=True)
    llm_output = Column(Text, nullable=True)
    tool_execution_trace = Column(Text, nullable=True)  # JSON

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

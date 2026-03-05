"""Pydantic schemas for documents."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    doc_type: str
    status: str
    page_count: Optional[int]
    transaction_count: int
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str
    encrypted: bool = False


class EncryptionCheckResponse(BaseModel):
    encrypted: bool
    file_id: str
    filename: str

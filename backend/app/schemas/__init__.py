"""Pydantic schemas for user-related operations."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from .transaction import TransactionCreate, TransactionUpdate, TransactionResponse, CategoryFeedback
from .document import DocumentUploadResponse, DocumentResponse
from .chat import ChatSessionCreate, ChatSessionUpdate, ChatMessageResponse, ChatSessionResponse, ChatSessionListResponse
from .budget import BudgetBase, BudgetCreate, BudgetUpdate, BudgetResponse, BudgetProgressResponse


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    base_currency: Optional[str] = Field(None, min_length=3, max_length=3)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    base_currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

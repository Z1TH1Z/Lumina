"""Pydantic schemas for chat history."""

from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"


class ChatSessionUpdate(BaseModel):
    title: str


class ChatMessageBase(BaseModel):
    role: str
    content: str
    sources_json: Optional[str] = None


class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

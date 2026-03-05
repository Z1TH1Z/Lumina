"""Pydantic schemas for transactions."""

from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal


class TransactionCreate(BaseModel):
    date: datetime
    description: str
    merchant: Optional[str] = None
    amount: float
    currency: str = "USD"
    category: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    date: datetime
    description: str
    merchant: Optional[str]
    amount: float
    currency: str
    category: str
    category_confidence: Optional[float]
    is_anomaly: bool
    anomaly_score: Optional[float]
    anomaly_explanation: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    anomaly_confirmed: Optional[bool] = None


class CategoryFeedback(BaseModel):
    transaction_id: int
    correct_category: str

class Anomaly(BaseModel):
    transaction_id: Any
    transaction: Optional[Any] = None
    z_score: Decimal
    explanation: str
    detected_at: datetime

class Forecast(BaseModel):
    period_months: int
    predicted_amount: Decimal
    confidence_interval_lower: Decimal
    confidence_interval_upper: Decimal
    category: Optional[str] = None

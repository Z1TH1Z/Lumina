from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class BudgetBase(BaseModel):
    category: str = Field(..., description="The transaction category this budget applies to")
    amount: float = Field(..., gt=0, description="The budget amount limit")
    month: date = Field(..., description="The month this budget applies to (must be the 1st of the month)")


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)


class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BudgetProgressResponse(BaseModel):
    category: str
    budget_amount: float
    spent_amount: float
    percentage_used: float
    is_exceeded: bool
    month: date

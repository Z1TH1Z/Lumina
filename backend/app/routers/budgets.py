from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from typing import List

from app.api.dependencies import get_db
from app.models.user import User
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetProgressResponse
from app.api.dependencies import get_current_user


router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new monthly budget for a category."""
    # Check if budget already exists for this category/month
    query = select(Budget).where(
        Budget.user_id == current_user.id,
        Budget.category == budget_in.category,
        Budget.month == budget_in.month
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Budget already exists for this category and month"
        )
        
    budget = Budget(
        user_id=current_user.id,
        category=budget_in.category,
        amount=budget_in.amount,
        month=budget_in.month
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


@router.get("/", response_model=List[BudgetResponse])
async def get_budgets(
    month: date = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all budgets for the user. Optionally filter by month."""
    query = select(Budget).where(Budget.user_id == current_user.id)
    if month:
        query = query.where(Budget.month == month)
        
    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a budget amount."""
    query = select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    result = await db.execute(query)
    budget = result.scalar_one_or_none()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    if budget_in.amount is not None:
        budget.amount = budget_in.amount
        
    await db.commit()
    await db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a budget."""
    query = select(Budget).where(Budget.id == budget_id, Budget.user_id == current_user.id)
    result = await db.execute(query)
    budget = result.scalar_one_or_none()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
        
    await db.delete(budget)
    await db.commit()


@router.get("/progress", response_model=List[BudgetProgressResponse])
async def get_budget_progress(
    month: date = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current spend progress against all budgets for a given month."""
    if not month:
        # Default to current month's first day
        today = date.today()
        month = date(today.year, today.month, 1)
        
    # 1. Fetch budgets for this month
    budgets_query = select(Budget).where(
        Budget.user_id == current_user.id,
        Budget.month == month
    )
    b_result = await db.execute(budgets_query)
    budgets = b_result.scalars().all()
    
    if not budgets:
        return []
        
    categories = [b.category for b in budgets]
    budget_map = {b.category: b.amount for b in budgets}
    
    # Calculate end of month for transaction filtering
    import calendar
    last_day = calendar.monthrange(month.year, month.month)[1]
    end_date = date(month.year, month.month, last_day)
    
    # 2. Sum transactions for these categories in this month
    # amount is typically negative for expenses in transactions, so we'll abs() it or sum(amount) and negate.
    t_query = select(
        Transaction.category,
        func.sum(Transaction.amount).label("total_spent")
    ).where(
        Transaction.user_id == current_user.id,
        Transaction.category.in_(categories),
        Transaction.date >= month,
        Transaction.date <= end_date,
        Transaction.amount < 0  # Only consider outgoing expenses mapped to budgets
    ).group_by(Transaction.category)
    
    t_result = await db.execute(t_query)
    spent_map = {row.category: abs(row.total_spent) for row in t_result.all()}
    
    progress_list = []
    for cat in categories:
        budget_amt = budget_map[cat]
        spent_amt = spent_map.get(cat, 0.0)
        pct = (spent_amt / budget_amt) * 100 if budget_amt > 0 else 0
        
        progress_list.append(BudgetProgressResponse(
            category=cat,
            budget_amount=budget_amt,
            spent_amount=spent_amt,
            percentage_used=round(pct, 2),
            is_exceeded=spent_amt > budget_amt,
            month=month
        ))
        
    return progress_list

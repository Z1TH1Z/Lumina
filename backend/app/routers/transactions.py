"""Transactions API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.api.dependencies import get_db
from app.models.user import User
from app.models.transaction import Transaction, TransactionCategory
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate, CategoryFeedback
from app.api.dependencies import get_current_user
from app.services.categorization import classify_transaction
from app.services.forex import convert_currency

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    category: Optional[str] = None,
    is_anomaly: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List transactions with optional filters."""
    query = select(Transaction).where(Transaction.user_id == current_user.id)

    if category:
        query = query.where(Transaction.category == category)

    if is_anomaly is not None:
        query = query.where(Transaction.is_anomaly == is_anomaly)

    query = query.order_by(Transaction.date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    txn_data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually create a transaction."""
    # Auto-classify if no category provided
    if not txn_data.category:
        classification = classify_transaction(txn_data.description, txn_data.merchant, txn_data.amount)
        cat = classification["category"]
        confidence = classification["confidence"]
    else:
        cat = txn_data.category
        confidence = 1.0

    txn = Transaction(
        user_id=current_user.id,
        date=txn_data.date,
        description=txn_data.description,
        merchant=txn_data.merchant,
        amount=txn_data.amount,
        currency=txn_data.currency,
        category=cat,
        category_confidence=confidence,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return txn


@router.put("/{txn_id}", response_model=TransactionResponse)
async def update_transaction(
    txn_id: int,
    update: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a transaction (e.g., confirm anomaly, correct category)."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == txn_id, Transaction.user_id == current_user.id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if update.category:
        txn.user_corrected_category = update.category

    if update.anomaly_confirmed is not None:
        txn.anomaly_confirmed = update.anomaly_confirmed

    await db.flush()
    await db.refresh(txn)
    return txn


@router.post("/feedback")
async def submit_category_feedback(
    feedback: CategoryFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit category correction feedback for adaptive learning."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == feedback.transaction_id, Transaction.user_id == current_user.id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.user_corrected_category = feedback.correct_category

    return {"message": "Feedback recorded", "transaction_id": txn.id, "corrected_category": feedback.correct_category}


@router.get("/summary")
async def transaction_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get spending summary by category, converted to the user's base currency."""
    result = await db.execute(select(Transaction).where(Transaction.user_id == current_user.id))
    transactions = result.scalars().all()

    category_data = {}
    total_spending = 0.0

    for txn in transactions:
        cat = txn.category.value if hasattr(txn.category, 'value') else str(txn.category)
        
        # Convert amount to user's base currency
        converted_amt = await convert_currency(txn.amount, txn.currency, current_user.base_currency)
        
        if cat not in category_data:
            category_data[cat] = {"count": 0, "total": 0.0}
            
        category_data[cat]["count"] += 1
        category_data[cat]["total"] += converted_amt
        
        # Only count negative values as "spending"
        if converted_amt < 0:
            total_spending += abs(converted_amt)

    categories = []
    for cat, data in category_data.items():
        avg = data["total"] / data["count"] if data["count"] > 0 else 0
        categories.append({
            "category": cat,
            "count": data["count"],
            "total": round(data["total"], 2),
            "average": round(avg, 2),
        })

    return {
        "categories": categories,
        "total_transactions": len(transactions),
        "total_spending": round(total_spending, 2),
        "base_currency": current_user.base_currency
    }

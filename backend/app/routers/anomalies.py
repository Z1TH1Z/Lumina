"""Anomaly detection API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.api.dependencies import get_current_user
from app.services.anomaly import detect_anomalies_statistical, detect_anomalies_by_category, generate_anomaly_explanation

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])


@router.post("/detect")
async def run_anomaly_detection(
    z_threshold: float = 2.5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run anomaly detection on all user transactions."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id).order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {"anomalies": [], "total_checked": 0}

    # Convert to dicts
    txn_dicts = [
        {
            "id": t.id,
            "date": str(t.date),
            "description": t.description,
            "merchant": t.merchant,
            "amount": t.amount,
            "category": t.category.value if hasattr(t.category, 'value') else str(t.category),
        }
        for t in transactions
    ]

    # Run statistical detection
    results = detect_anomalies_statistical(txn_dicts, z_threshold)

    # Update database records
    anomaly_count = 0
    for r in results:
        if r.get("is_anomaly"):
            anomaly_count += 1
            txn_result = await db.execute(select(Transaction).where(Transaction.id == r["id"]))
            txn = txn_result.scalar_one_or_none()
            if txn:
                txn.is_anomaly = True
                txn.anomaly_score = r.get("anomaly_score", 0)

    anomalies = [r for r in results if r.get("is_anomaly")]

    return {
        "anomalies": anomalies,
        "total_checked": len(transactions),
        "anomaly_count": anomaly_count,
        "threshold": z_threshold,
    }


@router.get("/")
async def list_anomalies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all flagged anomalies."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id, Transaction.is_anomaly == True)
        .order_by(Transaction.anomaly_score.desc())
    )
    transactions = result.scalars().all()

    return {
        "anomalies": [
            {
                "id": t.id,
                "date": str(t.date),
                "description": t.description,
                "merchant": t.merchant,
                "amount": t.amount,
                "category": t.category.value if hasattr(t.category, 'value') else str(t.category),
                "anomaly_score": t.anomaly_score,
                "anomaly_explanation": t.anomaly_explanation,
                "confirmed": t.anomaly_confirmed,
            }
            for t in transactions
        ],
        "count": len(transactions),
    }


@router.post("/{txn_id}/explain")
async def explain_anomaly(
    txn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate LLM explanation for a specific anomaly."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == txn_id,
            Transaction.user_id == current_user.id,
            Transaction.is_anomaly == True,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    explanation = await generate_anomaly_explanation({
        "date": str(txn.date),
        "description": txn.description,
        "merchant": txn.merchant,
        "amount": txn.amount,
        "category": txn.category.value if hasattr(txn.category, 'value') else str(txn.category),
        "anomaly_score": txn.anomaly_score,
        "z_score": (txn.anomaly_score or 0) * 10,
    })

    txn.anomaly_explanation = explanation
    return {"explanation": explanation, "transaction_id": txn_id}


@router.put("/{txn_id}/confirm")
async def confirm_anomaly(
    txn_id: int,
    is_legitimate: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User confirms or dismisses an anomaly."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == txn_id, Transaction.user_id == current_user.id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.anomaly_confirmed = not is_legitimate
    if is_legitimate:
        txn.is_anomaly = False

    return {"message": "Anomaly status updated", "transaction_id": txn_id, "is_anomaly": txn.is_anomaly}

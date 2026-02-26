"""Forecasting API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.api.dependencies import get_current_user
from app.services.forecasting import forecast_values, forecast_savings, generate_cash_flow_projection
from app.services.forex import convert_currency

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])


@router.get("/spending")
async def forecast_spending(
    periods: int = Query(default=6, ge=1, le=24),
    method: str = Query(default="exponential", regex="^(linear|exponential|moving_average)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast future spending based on historical data."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id, Transaction.amount < 0)
        .order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {"message": "No spending data available", "forecast": []}

    # Group by month and convert currencies
    monthly_spending = {}
    for txn in transactions:
        month_key = txn.date.strftime("%Y-%m")
        converted_amt = await convert_currency(txn.amount, txn.currency, current_user.base_currency)
        monthly_spending[month_key] = monthly_spending.get(month_key, 0) + abs(converted_amt)
        
    monthly_spending = dict(sorted(monthly_spending.items()))
    amounts = list(monthly_spending.values())

    forecast = forecast_values(amounts, periods=periods, method=method)
    forecast["months"] = list(monthly_spending.keys())
    forecast["base_currency"] = current_user.base_currency

    return forecast


@router.get("/savings")
async def forecast_savings_rate(
    periods: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast savings based on income and expense trends."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id).order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {"message": "No data available"}

    # Split income and expenses
    income_monthly = {}
    expense_monthly = {}

    for txn in transactions:
        month_key = txn.date.strftime("%Y-%m")
        converted_amt = await convert_currency(txn.amount, txn.currency, current_user.base_currency)
        if converted_amt > 0:
            income_monthly[month_key] = income_monthly.get(month_key, 0) + converted_amt
        else:
            expense_monthly[month_key] = expense_monthly.get(month_key, 0) + abs(converted_amt)

    all_months = sorted(set(list(income_monthly.keys()) + list(expense_monthly.keys())))
    income_vals = [income_monthly.get(m, 0) for m in all_months]
    expense_vals = [expense_monthly.get(m, 0) for m in all_months]

    forecast = forecast_savings(income_vals, expense_vals, periods=periods)
    forecast["months"] = all_months
    forecast["base_currency"] = current_user.base_currency

    return forecast


@router.get("/cashflow")
async def cash_flow_projection(
    periods: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate cash flow projection."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == current_user.id).order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {"message": "No data available"}

    txn_dicts = []
    for txn in transactions:
        converted_amt = await convert_currency(txn.amount, txn.currency, current_user.base_currency)
        txn_dicts.append({
            "date": txn.date.isoformat(),
            "amount": converted_amt,
            "category": txn.category.value if hasattr(txn.category, 'value') else str(txn.category),
            "currency": current_user.base_currency
        })

    result = generate_cash_flow_projection(txn_dicts, periods=periods)
    result["base_currency"] = current_user.base_currency
    return result


def _group_by_month(transactions) -> dict:
    """Group transaction amounts by month."""
    monthly = {}
    for txn in transactions:
        month_key = txn.date.strftime("%Y-%m")
        monthly[month_key] = monthly.get(month_key, 0) + abs(txn.amount)
    return dict(sorted(monthly.items()))

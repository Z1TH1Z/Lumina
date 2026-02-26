"""Time-series forecasting service for financial projections."""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def simple_moving_average(values: list[float], window: int = 3) -> list[float]:
    """Calculate simple moving average."""
    if len(values) < window:
        return values
    result = []
    for i in range(len(values) - window + 1):
        avg = sum(values[i:i + window]) / window
        result.append(round(avg, 2))
    return result


def exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
    """Simple exponential smoothing."""
    if not values:
        return []
    result = [values[0]]
    for i in range(1, len(values)):
        smoothed = alpha * values[i] + (1 - alpha) * result[-1]
        result.append(round(smoothed, 2))
    return result


def linear_trend(values: list[float]) -> dict:
    """Calculate linear trend (slope and intercept)."""
    n = len(values)
    if n < 2:
        return {"slope": 0, "intercept": values[0] if values else 0}

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    return {"slope": round(slope, 4), "intercept": round(intercept, 2)}


def forecast_values(
    historical: list[float],
    periods: int = 6,
    method: str = "exponential",
) -> dict:
    """
    Generate forecast values with confidence intervals.

    Args:
        historical: List of historical values (e.g., monthly spending).
        periods: Number of periods to forecast.
        method: Forecasting method ('linear', 'exponential', 'moving_average').

    Returns:
        dict with forecast, confidence_lower, confidence_upper, and metadata.
    """
    if not historical:
        return {
            "forecast": [],
            "confidence_lower": [],
            "confidence_upper": [],
            "method": method,
            "historical_stats": {},
        }

    n = len(historical)
    mean = sum(historical) / n
    variance = sum((x - mean) ** 2 for x in historical) / max(n - 1, 1)
    std = math.sqrt(variance)

    forecast = []

    if method == "linear":
        trend = linear_trend(historical)
        for i in range(periods):
            val = trend["intercept"] + trend["slope"] * (n + i)
            forecast.append(round(val, 2))

    elif method == "exponential":
        smoothed = exponential_smoothing(historical)
        last_smoothed = smoothed[-1] if smoothed else mean
        trend = linear_trend(historical)
        for i in range(periods):
            val = last_smoothed + trend["slope"] * (i + 1)
            forecast.append(round(val, 2))

    elif method == "moving_average":
        window = min(3, n)
        ma = simple_moving_average(historical, window)
        last_ma = ma[-1] if ma else mean
        for i in range(periods):
            forecast.append(round(last_ma, 2))

    else:
        # Default to mean
        forecast = [round(mean, 2)] * periods

    # Confidence intervals (widening with forecast horizon)
    confidence_lower = []
    confidence_upper = []
    for i, val in enumerate(forecast):
        margin = std * (1 + 0.2 * (i + 1))  # Widen with each period
        confidence_lower.append(round(val - margin, 2))
        confidence_upper.append(round(val + margin, 2))

    return {
        "forecast": forecast,
        "confidence_lower": confidence_lower,
        "confidence_upper": confidence_upper,
        "method": method,
        "periods": periods,
        "historical_stats": {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "trend_slope": linear_trend(historical)["slope"],
            "data_points": n,
        },
    }


def forecast_savings(
    income_history: list[float],
    expense_history: list[float],
    periods: int = 6,
) -> dict:
    """Forecast savings based on income and expense trends."""
    income_forecast = forecast_values(income_history, periods, "exponential")
    expense_forecast = forecast_values(expense_history, periods, "exponential")

    savings_forecast = []
    savings_lower = []
    savings_upper = []

    for i in range(periods):
        savings = income_forecast["forecast"][i] - expense_forecast["forecast"][i]
        savings_forecast.append(round(savings, 2))

        lower = income_forecast["confidence_lower"][i] - expense_forecast["confidence_upper"][i]
        upper = income_forecast["confidence_upper"][i] - expense_forecast["confidence_lower"][i]
        savings_lower.append(round(lower, 2))
        savings_upper.append(round(upper, 2))

    return {
        "savings_forecast": savings_forecast,
        "savings_lower": savings_lower,
        "savings_upper": savings_upper,
        "income_forecast": income_forecast,
        "expense_forecast": expense_forecast,
    }


def generate_cash_flow_projection(
    transactions: list[dict],
    periods: int = 6,
) -> dict:
    """Generate a month-by-month cash flow projection from transactions."""
    # Group transactions by month
    monthly: dict[str, dict] = {}
    for txn in transactions:
        date_str = str(txn.get("date", ""))
        try:
            if "T" in date_str:
                date = datetime.fromisoformat(date_str)
            else:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")
        except (ValueError, TypeError):
            continue

        if month_key not in monthly:
            monthly[month_key] = {"income": 0, "expenses": 0}

        amount = txn.get("amount", 0)
        if amount > 0:
            monthly[month_key]["income"] += amount
        else:
            monthly[month_key]["expenses"] += abs(amount)

    if not monthly:
        return {"months": [], "projection": []}

    sorted_months = sorted(monthly.keys())
    income_vals = [monthly[m]["income"] for m in sorted_months]
    expense_vals = [monthly[m]["expenses"] for m in sorted_months]

    return {
        "historical_months": sorted_months,
        "historical_income": income_vals,
        "historical_expenses": expense_vals,
        "projection": forecast_savings(income_vals, expense_vals, periods),
    }

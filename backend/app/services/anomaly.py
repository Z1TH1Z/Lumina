"""Hybrid anomaly detection service."""

import logging
import math
from typing import Optional
from app.services.llm import llm_service

logger = logging.getLogger(__name__)


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """Calculate the Z-score for a value."""
    if std == 0:
        return 0.0
    return abs((value - mean) / std)


def compute_statistics(amounts: list[float]) -> dict:
    """Compute basic statistics for a list of amounts."""
    if not amounts:
        return {"mean": 0, "std": 0, "median": 0, "min": 0, "max": 0}

    n = len(amounts)
    mean = sum(amounts) / n
    variance = sum((x - mean) ** 2 for x in amounts) / max(n - 1, 1)
    std = math.sqrt(variance)
    sorted_amounts = sorted(amounts)
    median = sorted_amounts[n // 2] if n % 2 == 1 else (sorted_amounts[n // 2 - 1] + sorted_amounts[n // 2]) / 2

    return {
        "mean": round(mean, 2),
        "std": round(std, 2),
        "median": round(median, 2),
        "min": min(amounts),
        "max": max(amounts),
    }


def detect_anomalies_statistical(
    transactions: list[dict],
    z_threshold: float = 2.5,
) -> list[dict]:
    """
    Layer 1: Statistical anomaly detection using Z-scores.
    Marks transactions with anomaly_score and is_anomaly flag.
    """
    if not transactions:
        return []

    amounts = [abs(t.get("amount", 0)) for t in transactions]
    stats = compute_statistics(amounts)

    results = []
    for txn in transactions:
        amount = abs(txn.get("amount", 0))
        z_score = calculate_z_score(amount, stats["mean"], stats["std"])
        is_anomaly = z_score > z_threshold

        results.append({
            **txn,
            "anomaly_score": round(z_score / 10, 2),  # Normalize to 0-1 range roughly
            "is_anomaly": is_anomaly,
            "z_score": round(z_score, 2),
        })

    return results


def detect_anomalies_by_category(
    transactions: list[dict],
    z_threshold: float = 2.0,
) -> list[dict]:
    """Detect anomalies within each spending category."""
    # Group by category
    by_category: dict[str, list] = {}
    for txn in transactions:
        cat = txn.get("category", "other")
        by_category.setdefault(cat, []).append(txn)

    results = []
    for category, txns in by_category.items():
        amounts = [abs(t.get("amount", 0)) for t in txns]
        stats = compute_statistics(amounts)

        for txn in txns:
            amount = abs(txn.get("amount", 0))
            z_score = calculate_z_score(amount, stats["mean"], stats["std"])
            is_anomaly = z_score > z_threshold

            results.append({
                **txn,
                "anomaly_score": round(min(z_score / 5, 1.0), 2),
                "is_anomaly": is_anomaly,
                "category_stats": stats,
            })

    return results


async def generate_anomaly_explanation(transaction: dict) -> str:
    """Layer 3: Generate a natural-language explanation for an anomaly using LLM."""
    prompt = f"""Analyze this financial transaction that was flagged as a potential anomaly:

Transaction Details:
- Date: {transaction.get('date', 'Unknown')}
- Description: {transaction.get('description', 'Unknown')}
- Merchant: {transaction.get('merchant', 'Unknown')}
- Amount: ${transaction.get('amount', 0):.2f}
- Category: {transaction.get('category', 'Unknown')}
- Anomaly Score: {transaction.get('anomaly_score', 0)}
- Z-Score: {transaction.get('z_score', 0)}

Provide a brief, clear explanation of why this transaction might be anomalous. Consider:
1. Is the amount unusually high/low for this category?
2. Could this be a legitimate expense (e.g., annual payment)?
3. What should the user check?

Keep the explanation under 100 words."""

    system_prompt = "You are a financial analyst assistant. Provide concise, helpful anomaly explanations."

    if await llm_service.is_available():
        return await llm_service.generate(prompt, system_prompt=system_prompt)
    else:
        # Fallback explanation
        amount = abs(transaction.get("amount", 0))
        z_score = transaction.get("z_score", 0)
        return (
            f"This transaction of ${amount:.2f} was flagged because it deviates significantly "
            f"from your typical spending pattern (Z-score: {z_score:.1f}). "
            f"Please verify this is a legitimate expense."
        )

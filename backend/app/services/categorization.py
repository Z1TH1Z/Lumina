"""Expense categorization service using ML classification."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Category keyword mappings for rule-based classification
CATEGORY_KEYWORDS = {
    "housing": ["rent", "mortgage", "property", "real estate", "apartment", "housing", "lease", "hoa"],
    "food": ["restaurant", "grocery", "food", "coffee", "cafe", "dining", "pizza", "burger", "doordash",
             "ubereats", "grubhub", "starbucks", "mcdonald", "chipotle", "subway", "whole foods",
             "trader joe", "kroger", "walmart", "target"],
    "transport": ["uber", "lyft", "gas", "fuel", "parking", "toll", "transit", "metro", "bus",
                  "airline", "flight", "car", "auto", "vehicle", "taxi", "shell", "chevron", "bp"],
    "utilities": ["electric", "water", "gas", "internet", "phone", "cable", "utility", "power",
                  "verizon", "at&t", "comcast", "spectrum", "t-mobile"],
    "entertainment": ["netflix", "spotify", "hulu", "disney", "movie", "theater", "gaming", "steam",
                      "playstation", "xbox", "concert", "ticket", "entertainment", "youtube", "twitch"],
    "healthcare": ["doctor", "hospital", "pharmacy", "medical", "dental", "health", "clinic",
                   "cvs", "walgreens", "insurance", "prescription", "optometry"],
    "shopping": ["amazon", "ebay", "shop", "store", "mall", "clothing", "fashion", "nike", "adidas",
                 "best buy", "apple", "costco", "home depot", "lowes", "ikea"],
    "income": ["salary", "payroll", "deposit", "income", "dividend", "interest", "refund", "cashback"],
    "transfer": ["transfer", "zelle", "venmo", "paypal", "wire", "ach"],
    "investment": ["invest", "stock", "etf", "mutual fund", "brokerage", "robinhood", "fidelity",
                   "vanguard", "schwab", "crypto", "bitcoin"],
    "insurance": ["insurance", "premium", "geico", "allstate", "state farm", "progressive"],
    "education": ["tuition", "school", "university", "college", "course", "udemy", "coursera",
                  "textbook", "student loan"],
}


def classify_transaction(description: str, merchant: Optional[str] = None, amount: float = 0) -> dict:
    """
    Classify a transaction into a category.
    Returns: {"category": str, "confidence": float}
    """
    text = f"{description} {merchant or ''}".lower().strip()

    # Score each category
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                # Longer keyword matches are more specific and get higher scores
                score += len(keyword)
        if score > 0:
            scores[category] = score

    if scores:
        best_category = max(scores, key=scores.get)
        # Normalize confidence to 0-1 range
        max_possible = max(len(kw) for kw in CATEGORY_KEYWORDS[best_category])
        confidence = min(scores[best_category] / (max_possible * 2), 0.99)
        return {"category": best_category, "confidence": round(confidence, 2)}

    # Income detection by amount sign
    if amount > 0:
        return {"category": "income", "confidence": 0.5}

    return {"category": "other", "confidence": 0.3}


def batch_classify(transactions: list[dict]) -> list[dict]:
    """Classify a batch of transactions."""
    results = []
    for txn in transactions:
        classification = classify_transaction(
            description=txn.get("description", ""),
            merchant=txn.get("merchant"),
            amount=txn.get("amount", 0),
        )
        results.append({**txn, **classification})
    return results

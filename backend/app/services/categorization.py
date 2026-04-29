"""Expense categorization service: rule engine → ML classifier → keyword fallback."""

import re
import logging
from datetime import datetime, date as date_type
from typing import Optional
from collections import defaultdict

from app.core.constants import CATEGORIZATION_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Merchant Normalization Map
# ---------------------------------------------------------------------------

MERCHANT_MAP: dict[str, str] = {
    # Amazon variants
    "amzn": "amazon", "amazon pay": "amazon", "amazon prime": "amazon",
    "amazon seller": "amazon", "amzn mktp": "amazon",
    # Food delivery (India)
    "swiggy instamart": "swiggy", "swiggit": "swiggy",
    "zomato order": "zomato",
    "blinkit": "blinkit", "zepto": "zepto",
    "dunzo": "dunzo",
    # Ride hailing (India)
    "ola cabs": "ola", "olacabs": "ola",
    "rapido bike": "rapido",
    # Telecom (India)
    "jio recharge": "jio", "reliance jio": "jio",
    "airtel prepaid": "airtel", "airtel broadband": "airtel",
    "bsnl broadband": "bsnl",
    "vi mobile": "vodafone",
    # Payments (India)
    "paytm wallet": "paytm", "paytm mall": "paytm",
    "phonepe upi": "phonepe",
    "google pay": "gpay", "googlepay": "gpay",
    # Investment (India)
    "zerodha broking": "zerodha",
    "groww mutual": "groww",
    "upstox": "upstox",
    # Food chains (India)
    "mcdonald": "mcdonalds", "mc donalds": "mcdonalds",
    "burger king india": "burger king",
    "pizza hut india": "pizza hut",
    "domino": "dominos",
    # E-commerce (India)
    "flipkart internet": "flipkart",
    "myntra designs": "myntra",
    "meesho": "meesho",
    # Global
    "uber technologies": "uber", "uber eats": "ubereats",
    "lyft inc": "lyft",
    "netflix.com": "netflix",
    "spotify ab": "spotify",
    "apple.com/bill": "apple",
    "google *": "google",
    "microsoft": "microsoft",
    "paypal": "paypal",
}


def normalize_merchant(merchant: str) -> str:
    """Apply MERCHANT_MAP to normalize known merchant variants."""
    if not merchant:
        return merchant
    m = merchant.lower().strip()
    for pattern, canonical in MERCHANT_MAP.items():
        if pattern in m:
            return canonical
    return m


# ---------------------------------------------------------------------------
# 2. Text Cleaning
# ---------------------------------------------------------------------------

# Prefixes common in bank statement narrations that add no signal
_NARRATION_PREFIXES = re.compile(
    r'^(pos|debit|credit|ach|wire|transfer|atm|neft|imps|upi|rtgs|nach|emi|int|chq|clg)\s*[/\-]?\s*',
    re.IGNORECASE,
)
# Remove reference numbers, UPI IDs, long alphanumeric tokens.
# Note: clean_text/_rule_text lowercase input before applying this regex.
_NOISE_PATTERNS = re.compile(r'\b(\d{6,}|[a-z0-9]{16,})\b')
# Keep only letters and spaces after cleaning
_NON_ALPHA = re.compile(r'[^a-z\s]')


def clean_text(text: str) -> str:
    """Lowercase, strip noise prefixes, and normalize a transaction description.
    Used for ML/keyword matching where a clean vocabulary matters more than context.
    """
    text = text.lower().strip()
    text = _NARRATION_PREFIXES.sub('', text)
    text = _NOISE_PATTERNS.sub('', text)
    text = _NON_ALPHA.sub(' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _rule_text(text: str) -> str:
    """Light normalization for the rule engine — keep prefixes (neft/upi/etc.)
    since rules like 'neft to' and 'upi transfer' rely on them for precision.
    """
    text = text.lower().strip()
    text = _NOISE_PATTERNS.sub('', text)   # remove ref numbers only
    text = _NON_ALPHA.sub(' ', text)
    return re.sub(r'\s+', ' ', text).strip()


# ---------------------------------------------------------------------------
# 3. Rule Engine (deterministic, high-precision)
# ---------------------------------------------------------------------------

# Each entry: (keywords_any_match, optional_amount_condition, category)
# Rules are checked in order; first match wins.
_RULES: list[tuple[list[str], Optional[callable], str]] = [
    # Income signals — check before food/shopping to avoid "salary" in other
    (["salary", "payroll", "pay credit", "ctc", "stipend"], None, "income"),
    (["dividend", "interest credited", "int pd", "maturity"], None, "income"),
    (["refund", "cashback", "cash back", "reversal"], None, "income"),

    # ATM / cash
    (["atm", "cash withdrawal", "cash wdl"], None, "cash"),

    # Food delivery & restaurants (India-first)
    (["zomato", "swiggy", "blinkit", "zepto", "dunzo", "instamart"], None, "food"),
    (["restaurant", "cafe", "coffee", "bistro", "dhaba", "hotel kitchen",
      "mcdonalds", "burger king", "dominos", "pizza hut", "kfc", "subway",
      "starbucks", "chaayos", "ccd", "barista"], None, "food"),
    (["grocery", "supermarket", "hypermarket", "big bazaar", "dmart",
      "reliance fresh", "more megastore", "nature basket", "spencer"], None, "food"),
    (["ubereats", "doordash", "grubhub"], None, "food"),

    # Transport
    (["uber", "ola", "rapido", "meru", "lyft", "taxi", "cab"], None, "transport"),
    (["metro", "dmrc", "bmtc", "ksrtc", "irctc", "railway", "train ticket",
      "bus ticket", "redbus"], None, "transport"),
    (["petrol", "diesel", "fuel", "hp pump", "iocl", "bpcl", "shell",
      "gas station", "bp ", "chevron"], None, "transport"),
    (["parking", "fastag", "toll"], None, "transport"),
    (["flight", "airline", "indigo", "air india", "spicejet", "vistara",
      "makemytrip", "goibibo", "cleartrip"], None, "transport"),

    # Utilities
    (["electricity", "bescom", "msedcl", "tata power", "adani electricity",
      "bses", "kseb", "tangedco"], None, "utilities"),
    (["water bill", "bwssb", "water supply"], None, "utilities"),
    (["jio", "airtel", "bsnl", "vodafone", "vi ", "idea ", "tata sky",
      "dish tv", "sun direct", "d2h"], None, "utilities"),
    (["broadband", "wifi bill", "internet bill", "fiber"], None, "utilities"),

    # Entertainment
    (["netflix", "spotify", "hotstar", "prime video", "zee5", "sonyliv",
      "mxplayer", "jiocinema", "youtube premium", "hulu", "disney",
      "apple tv", "twitch"], None, "entertainment"),
    (["movie", "cinema", "pvr", "inox", "bookmyshow", "concert", "gaming",
      "steam", "playstation", "xbox", "epic games"], None, "entertainment"),

    # Healthcare
    (["pharmacy", "chemist", "medical store", "apollo pharmacy",
      "medplus", "netmeds", "1mg", "pharmeasy", "healthkart"], None, "healthcare"),
    (["hospital", "clinic", "doctor", "dental", "optometry", "diagnostic",
      "lab test", "practo", "lybrate"], None, "healthcare"),

    # Insurance (life, health, vehicle — all premiums go here)
    (["insurance premium", "life insurance", "mediclaim", "lic",
      "star health", "hdfc life", "icici pru", "bajaj allianz",
      "niva bupa", "max life", "new india assurance",
      "car insurance", "vehicle insurance", "two wheeler insurance",
      "term insurance", "ulip", "geico", "allstate", "progressive",
      "state farm"], None, "insurance"),

    # Shopping / E-commerce
    (["amazon", "flipkart", "myntra", "meesho", "ajio", "nykaa", "tata cliq",
      "snapdeal", "ebay", "aliexpress"], None, "shopping"),
    (["clothing", "fashion", "apparel", "nike", "adidas", "puma", "zara",
      "h&m", "levi", "woodland"], None, "shopping"),
    (["electronics", "mobile", "laptop", "apple store", "samsung store",
      "croma", "vijay sales", "reliance digital", "best buy"], None, "shopping"),
    (["home depot", "ikea", "pepperfry", "urban ladder", "blinds",
      "furnishing", "decor"], None, "shopping"),

    # Investment / Brokerage
    (["zerodha", "groww", "upstox", "kuvera", "coin by zerodha", "fidelity",
      "vanguard", "schwab", "robinhood"], None, "investment"),
    (["mutual fund", "sip ", "equity", "stock purchase", "demat",
      "brokerage", "etf", "crypto", "bitcoin"], None, "investment"),
    (["fd ", "fixed deposit", "rd ", "recurring deposit", "ppf", "nps",
      "sovereign gold bond"], None, "investment"),

    # Education
    (["udemy", "coursera", "byju", "byjus", "unacademy", "vedantu", "upgrad",
      "simplilearn", "khan academy", "edx"], None, "education"),
    (["school fee", "tuition fee", "university fee", "college fee",
      "hostel fee", "exam fee", "student loan"], None, "education"),

    # Transfers
    (["transfer to", "neft to", "imps to", "rtgs to", "upi to",
      "upi transfer", "fund transfer", "money transfer",
      "zelle", "venmo", "paypal transfer", "wise", "remittance"], None, "transfer"),

    # Housing
    (["rent", "mortgage", "maintenance charges", "society charges",
      "property tax", "hoa", "apartment", "lease"], None, "housing"),
]


def _kw_match(kw: str, text: str) -> bool:
    """Match keyword against text using word boundaries to avoid substring false-positives."""
    return bool(re.search(r'\b' + re.escape(kw.strip()) + r'\b', text))


def rule_engine(text: str, amount: float = 0.0) -> Optional[tuple[str, float]]:
    """
    Apply deterministic rules. Returns (category, confidence) or None.
    Confidence is 0.95 for rule matches — rules are high-precision.
    """
    for keywords, condition, category in _RULES:
        if any(_kw_match(kw, text) for kw in keywords):
            if condition is None or condition(amount):
                return category, 0.95
    return None


# ---------------------------------------------------------------------------
# 4. Keyword Scorer (fallback — weighted, existing logic improved)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "housing": [
        "rent", "mortgage", "property", "apartment", "lease", "hoa", "housing",
        "landlord", "rental", "tenant", "society", "maintenance", "home loan", "flat",
    ],
    "food": ["restaurant", "grocery", "food", "coffee", "cafe", "dining", "pizza",
             "burger", "starbucks", "mcdonald", "chipotle", "whole foods",
             "trader joe", "kroger", "walmart", "target"],
    "transport": ["uber", "lyft", "gas", "fuel", "parking", "toll", "transit",
                  "metro", "bus", "airline", "flight", "car", "taxi", "shell"],
    "utilities": ["electric", "water", "internet", "phone", "cable", "utility",
                  "power", "verizon", "comcast", "spectrum"],
    "entertainment": ["netflix", "spotify", "hulu", "disney", "movie", "theater",
                      "gaming", "steam", "concert", "ticket", "youtube", "twitch"],
    "healthcare": ["doctor", "hospital", "pharmacy", "medical", "dental", "health",
                   "clinic", "cvs", "walgreens", "prescription"],
    "shopping": ["amazon", "ebay", "shop", "store", "mall", "clothing", "fashion",
                 "nike", "adidas", "best buy", "apple", "costco", "ikea"],
    "income": ["salary", "payroll", "deposit", "income", "dividend", "interest",
               "refund", "cashback"],
    "transfer": ["transfer", "zelle", "venmo", "paypal", "wire", "ach"],
    "investment": ["invest", "stock", "etf", "mutual fund", "brokerage",
                   "robinhood", "fidelity", "vanguard", "schwab", "crypto"],
    "insurance": ["insurance", "premium", "geico", "allstate", "state farm",
                  "progressive"],
    "education": ["tuition", "school", "university", "college", "course", "udemy",
                  "coursera", "textbook", "student loan"],
    "cash": ["atm", "cash withdrawal", "cash wdl"],
}


def _keyword_scorer(text: str, amount: float = 0.0) -> tuple[str, float]:
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(len(kw) for kw in keywords if _kw_match(kw, text))
        if score > 0:
            scores[category] = score

    if scores:
        best = max(scores, key=scores.get)
        max_possible = max(len(kw) for kw in CATEGORY_KEYWORDS[best])
        confidence = min(scores[best] / (max_possible * 2), 0.85)
        return best, round(confidence, 2)

    if amount > 0:
        return "income", 0.4

    return "other", 0.2


# ---------------------------------------------------------------------------
# 5. Feature Extraction (used by ML model training + prediction)
# ---------------------------------------------------------------------------

def extract_features(
    description: str,
    merchant: Optional[str],
    amount: float,
    txn_date: Optional[date_type] = None,
) -> dict:
    """Build structured numeric features for a transaction."""
    d = txn_date or datetime.today().date()
    return {
        "amount_abs": abs(amount),
        "is_debit": 1 if amount < 0 else 0,
        "is_credit": 1 if amount > 0 else 0,
        "is_large": 1 if abs(amount) > 10000 else 0,
        "is_small": 1 if abs(amount) < 100 else 0,
        "day_of_week": d.weekday(),          # 0=Mon … 6=Sun
        "is_weekend": 1 if d.weekday() >= 5 else 0,
        "month": d.month,
    }


# ---------------------------------------------------------------------------
# 6. Recurring Transaction Detection
# ---------------------------------------------------------------------------

def detect_recurring(transactions: list[dict], tolerance: float = 0.05) -> list[dict]:
    """
    Flag transactions that appear to recur monthly (same merchant, similar amount).

    Args:
        transactions: list of dicts with keys: date, merchant, amount
        tolerance: fractional tolerance for amount matching (default 5%)

    Returns:
        Same list with `is_recurring` bool added to each dict.
    """
    from collections import defaultdict
    import math

    # Build groups: merchant → list of (year_month, amount)
    groups: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for txn in transactions:
        raw_date = txn.get("date", "")
        merchant = normalize_merchant(txn.get("merchant", ""))
        amount = float(txn.get("amount", 0))
        if not merchant or amount == 0:
            continue
        # Normalize date to YYYY-MM
        try:
            if isinstance(raw_date, (datetime, date_type)):
                ym = raw_date.strftime("%Y-%m")
            else:
                parsed = re.search(r'(\d{4}[-/]\d{2})|(\d{2}[-/]\d{2}[-/]\d{2,4})', str(raw_date))
                ym = parsed.group(0)[:7].replace('/', '-') if parsed else ""
        except Exception:
            ym = ""
        if ym:
            groups[merchant].append((ym, amount))

    # Find recurring merchants: appear in 2+ distinct months with similar amount
    recurring_merchants: set[str] = set()
    for merchant, entries in groups.items():
        months = {ym for ym, _ in entries}
        if len(months) < 2:
            continue
        avg_amount = sum(abs(a) for _, a in entries) / len(entries)
        if avg_amount == 0:
            continue
        all_similar = all(
            abs(abs(a) - avg_amount) / avg_amount <= tolerance
            for _, a in entries
        )
        if all_similar:
            recurring_merchants.add(merchant)

    # Tag each transaction
    result = []
    for txn in transactions:
        merchant = normalize_merchant(txn.get("merchant", ""))
        result.append({**txn, "is_recurring": merchant in recurring_merchants})
    return result


# ---------------------------------------------------------------------------
# 7. Hybrid Pipeline — Main Entry Point
# ---------------------------------------------------------------------------

def classify_transaction(
    description: str,
    merchant: Optional[str] = None,
    amount: float = 0.0,
    txn_date: Optional[date_type] = None,
    confidence_threshold: float = CATEGORIZATION_CONFIDENCE_THRESHOLD,
) -> dict:
    """
    Hybrid categorization pipeline:
        1. Clean & normalize text
        2. Rule engine  (returns if confidence >= 0.95)
        3. ML classifier (returns if confidence >= threshold)
        4. Keyword scorer (fallback)

    Returns:
        {"category": str, "confidence": float, "method": str}
    """
    # --- Step 1: clean ---
    norm_merchant = normalize_merchant(merchant or "")
    combined_raw = f"{description} {norm_merchant}".strip()
    # Rule engine uses light cleaning (keeps neft/upi/transfer prefixes for context)
    rule_input = _rule_text(combined_raw)
    # ML/keyword uses full cleaning (removes prefix noise for cleaner vocabulary)
    text = clean_text(combined_raw)

    # --- Step 2: rule engine ---
    rule_result = rule_engine(rule_input, amount)
    if rule_result:
        return {"category": rule_result[0], "confidence": rule_result[1], "method": "rule"}

    # --- Step 3: ML classifier (lazy import avoids circular deps) ---
    try:
        from app.services.ml_service import ml_service
        features = extract_features(description, merchant, amount, txn_date)
        cat, conf = ml_service.predict_category(text, features)
        if conf >= confidence_threshold:
            return {"category": cat, "confidence": conf, "method": "ml"}
    except Exception as e:
        logger.warning(
            "ML classifier unavailable; falling back to keyword tier (%s: %s)",
            type(e).__name__,
            e,
        )

    # --- Step 4: keyword scorer ---
    cat, conf = _keyword_scorer(text, amount)
    return {"category": cat, "confidence": conf, "method": "keyword"}


def batch_classify(transactions: list[dict]) -> list[dict]:
    """Classify a batch of transactions, optionally tagging recurring ones."""
    tagged = detect_recurring(transactions)
    results = []
    for txn in tagged:
        classification = classify_transaction(
            description=txn.get("description", ""),
            merchant=txn.get("merchant"),
            amount=float(txn.get("amount", 0)),
        )
        results.append({**txn, **classification})
    return results

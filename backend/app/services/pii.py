"""PII detection and masking service."""

import re
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Common PII patterns
PII_PATTERNS = {
    "ssn": {
        "pattern": r'\b\d{3}-\d{2}-\d{4}\b',
        "label": "SSN",
    },
    "credit_card": {
        "pattern": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "label": "CREDIT_CARD",
    },
    "email": {
        "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "label": "EMAIL",
    },
    "phone": {
        "pattern": r'\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "label": "PHONE",
    },
    "account_number": {
        "pattern": r'\b(?:account|acct)[\s#:]*\d{6,}\b',
        "label": "ACCOUNT_NUMBER",
    },
    "routing_number": {
        "pattern": r'\b(?:routing|aba)[\s#:]*\d{9}\b',
        "label": "ROUTING_NUMBER",
    },
}


def detect_pii(text: str) -> list[dict]:
    """Detect PII entities in text."""
    findings = []

    for pii_type, config in PII_PATTERNS.items():
        matches = re.finditer(config["pattern"], text, re.IGNORECASE)
        for match in matches:
            findings.append({
                "type": pii_type,
                "label": config["label"],
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
            })

    return findings


def mask_pii(text: str, method: str = "redact") -> dict:
    """
    Mask PII in text.

    Methods:
    - 'redact': Replace with [REDACTED]
    - 'hash': Replace with SHA-256 hash
    - 'token': Replace with type-specific token (e.g., [SSN_1])
    """
    findings = detect_pii(text)

    if not findings:
        return {"text": text, "findings": [], "pii_detected": False}

    # Sort by position (reverse) to maintain correct offsets
    findings.sort(key=lambda x: x["start"], reverse=True)

    masked_text = text
    token_counter: dict[str, int] = {}

    for finding in findings:
        if method == "redact":
            replacement = f"[REDACTED]"
        elif method == "hash":
            hash_val = hashlib.sha256(finding["text"].encode()).hexdigest()[:12]
            replacement = f"[HASH:{hash_val}]"
        elif method == "token":
            pii_type = finding["label"]
            token_counter[pii_type] = token_counter.get(pii_type, 0) + 1
            replacement = f"[{pii_type}_{token_counter[pii_type]}]"
        else:
            replacement = "[REDACTED]"

        masked_text = masked_text[:finding["start"]] + replacement + masked_text[finding["end"]:]

    return {
        "text": masked_text,
        "findings": [{"type": f["type"], "label": f["label"]} for f in findings],
        "pii_detected": True,
        "pii_count": len(findings),
    }


def sanitize_for_llm(text: str) -> str:
    """Sanitize text before sending to LLM by masking all PII."""
    result = mask_pii(text, method="token")
    return result["text"]

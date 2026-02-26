"""Document ingestion service: PDF parsing, OCR, and data extraction."""

import os
import json
import logging
import re
from datetime import datetime
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def extract_text_from_pdf(file_path: str) -> dict:
    """Extract text and tables from a PDF file."""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, using basic extraction")
        return _basic_extract(file_path)

    result = {"pages": [], "raw_text": "", "tables": [], "page_count": 0}

    try:
        with pdfplumber.open(file_path) as pdf:
            result["page_count"] = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                result["pages"].append({"page_num": i + 1, "text": page_text})
                result["raw_text"] += page_text + "\n"

                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        result["tables"].append({
                            "page_num": i + 1,
                            "data": table,
                        })
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        result["error"] = str(e)

    return result


def _basic_extract(file_path: str) -> dict:
    """Fallback extraction using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return {"raw_text": text, "page_count": len(doc), "pages": [], "tables": []}
    except Exception:
        return {"raw_text": "", "page_count": 0, "pages": [], "tables": []}


def extract_transactions_from_text(raw_text: str) -> list[dict]:
    """Parse raw text to extract transaction-like records."""
    transactions = []

    # Common patterns for financial data
    # Pattern: DATE DESCRIPTION AMOUNT
    patterns = [
        # MM/DD/YYYY Description $Amount or Amount
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+\$?([\-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        # YYYY-MM-DD Description Amount
        r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+\$?([\-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, raw_text)
        for match in matches:
            try:
                date_str, description, amount_str = match
                amount = float(amount_str.replace(",", ""))
                transactions.append({
                    "date": date_str,
                    "description": description.strip(),
                    "amount": amount,
                    "merchant": _extract_merchant(description.strip()),
                })
            except (ValueError, IndexError):
                continue

    return transactions


def extract_transactions_from_tables(tables: list[dict]) -> list[dict]:
    """Extract transactions from detected table data."""
    transactions = []

    for table_info in tables:
        rows = table_info.get("data", [])
        if not rows or len(rows) < 2:
            continue

        # Try to identify columns by header
        header = [str(h).lower().strip() if h else "" for h in rows[0]]
        date_col = _find_column(header, ["date", "trans date", "transaction date", "posted"])
        desc_col = _find_column(header, ["description", "details", "transaction", "memo", "narration"])
        amount_col = _find_column(header, ["amount", "value", "debit", "credit"])

        if date_col is None or amount_col is None:
            continue

        for row in rows[1:]:
            try:
                if len(row) <= max(date_col, amount_col):
                    continue
                date_str = str(row[date_col] or "").strip()
                desc = str(row[desc_col] if desc_col is not None and desc_col < len(row) else "").strip()
                amount_str = str(row[amount_col] or "").strip()

                if not date_str or not amount_str:
                    continue

                amount = float(re.sub(r'[^\d.\-]', '', amount_str))
                transactions.append({
                    "date": date_str,
                    "description": desc,
                    "amount": amount,
                    "merchant": _extract_merchant(desc),
                })
            except (ValueError, IndexError):
                continue

    return transactions


def _find_column(header: list[str], keywords: list[str]) -> Optional[int]:
    for i, h in enumerate(header):
        for kw in keywords:
            if kw in h:
                return i
    return None


def _extract_merchant(description: str) -> str:
    """Extract a merchant name from a transaction description."""
    # Remove common prefixes
    desc = re.sub(r'^(POS|DEBIT|CREDIT|ACH|TRANSFER|CHECK|ATM|WIRE)\s+', '', description, flags=re.IGNORECASE)
    # Take first 2-3 meaningful words
    words = desc.split()[:3]
    return " ".join(words) if words else description


def process_document(file_path: str) -> dict:
    """Full pipeline: extract text, parse transactions, return structured data."""
    pdf_data = extract_text_from_pdf(file_path)

    # Extract from text
    text_transactions = extract_transactions_from_text(pdf_data.get("raw_text", ""))

    # Extract from tables
    table_transactions = extract_transactions_from_tables(pdf_data.get("tables", []))

    # Merge and deduplicate
    all_transactions = text_transactions + table_transactions

    return {
        "raw_text": pdf_data.get("raw_text", ""),
        "page_count": pdf_data.get("page_count", 0),
        "transactions": all_transactions,
        "transaction_count": len(all_transactions),
    }

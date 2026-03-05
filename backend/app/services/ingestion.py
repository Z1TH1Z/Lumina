"""Document ingestion service: PDF parsing, OCR, encryption detection, and data extraction."""

import os
import json
import logging
import re
import tempfile
from datetime import datetime
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# PDF Encryption Detection & Decryption
# ---------------------------------------------------------------------------

def check_pdf_encrypted(file_path: str) -> bool:
    """Check whether a PDF file is password-protected.

    Uses PyMuPDF (fitz) to detect encryption.  Returns True if the PDF
    requires a password to open, False otherwise.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        encrypted = doc.needs_pass
        doc.close()
        return bool(encrypted)
    except Exception as e:
        logger.error(f"Encryption check failed: {e}")
        # If we can't even open it, treat as not-encrypted and let
        # downstream extraction surface the real error.
        return False


def decrypt_pdf(file_path: str, password: str) -> str:
    """Decrypt a password-protected PDF and write the unlocked version to a
    temporary file.

    Tries PyMuPDF first; falls back to pikepdf for AES-256 encrypted PDFs
    that PyMuPDF cannot handle.

    Returns:
        Path to the decrypted (temporary) PDF file.

    Raises:
        ValueError: If the password is incorrect or decryption fails.
    """
    # --- Attempt 1: PyMuPDF ---
    try:
        import fitz
        doc = fitz.open(file_path)
        if doc.needs_pass:
            auth_ok = doc.authenticate(password)
            if not auth_ok:
                doc.close()
                raise ValueError("Incorrect password")
        # Save unlocked copy
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()  # Close handle first so fitz can write on Windows
        doc.save(tmp_path)
        doc.close()
        logger.info("PDF decrypted successfully via PyMuPDF")
        return tmp_path
    except ValueError:
        raise  # re-raise wrong-password errors immediately
    except Exception as e:
        logger.warning(f"PyMuPDF decryption failed ({e}), trying pikepdf…")

    # --- Attempt 2: pikepdf (handles AES-256) ---
    try:
        import pikepdf
    except ImportError:
        raise ValueError(
            "Could not decrypt this PDF. "
            "Install pikepdf (`pip install pikepdf`) for AES-256 support."
        )
    try:
        pdf = pikepdf.open(file_path, password=password)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()  # Close handle first so pikepdf can write on Windows
        pdf.save(tmp_path)
        pdf.close()
        logger.info("PDF decrypted successfully via pikepdf")
        return tmp_path
    except pikepdf._core.PasswordError:
        raise ValueError("Incorrect password")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


# ---------------------------------------------------------------------------
# PDF Text & Table Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_path: str, password: Optional[str] = None) -> dict:
    """Extract text and tables from a PDF file.

    If *password* is supplied the PDF is decrypted in-memory first; the
    decrypted bytes are never written to persistent storage.
    """
    # If a password is provided, decrypt first
    decrypted_path = None
    working_path = file_path

    if password:
        try:
            decrypted_path = decrypt_pdf(file_path, password)
            working_path = decrypted_path
        except ValueError:
            raise  # propagate bad-password errors

    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, using basic extraction")
        result = _basic_extract(working_path, password)
        _cleanup_temp(decrypted_path)
        return result

    result = {"pages": [], "raw_text": "", "tables": [], "page_count": 0}

    try:
        with pdfplumber.open(working_path) as pdf:
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
    finally:
        _cleanup_temp(decrypted_path)

    return result


def _basic_extract(file_path: str, password: Optional[str] = None) -> dict:
    """Fallback extraction using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        if password and doc.needs_pass:
            if not doc.authenticate(password):
                doc.close()
                raise ValueError("Incorrect password")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        result = {"raw_text": text, "page_count": len(doc), "pages": [], "tables": []}
        doc.close()
        return result
    except ValueError:
        raise
    except Exception:
        return {"raw_text": "", "page_count": 0, "pages": [], "tables": []}


def _cleanup_temp(path: Optional[str]):
    """Remove a temporary decrypted file if it exists."""
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Transaction Parsing
# ---------------------------------------------------------------------------

def extract_transactions_from_text(raw_text: str) -> list[dict]:
    """Parse raw text to extract transaction-like records."""
    transactions = []

    # 1. First, try the highly structured HDFC statement format:
    # Date  Narration  Chq./Ref.No.  Value Dt  Withdrawal Amt.  Deposit Amt.  Closing Balance
    hdfc_pattern = r'(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(?:\d{16}|[A-Z0-9]+)\s+(?:\d{2}/\d{2}/\d{2})\s+([\d,.]+)?\s*([\d,.]+)?\s+[\d,.]+'
    
    for match in re.finditer(hdfc_pattern, raw_text):
        date_str = match.group(1)
        description = match.group(2).strip()
        withdrawal_str = match.group(3)
        deposit_str = match.group(4)
        
        try:
            amount = 0.0
            if withdrawal_str and withdrawal_str.strip():
                amount = -float(withdrawal_str.replace(',', ''))
            elif deposit_str and deposit_str.strip():
                amount = float(deposit_str.replace(',', ''))
            
            if amount != 0.0:
                transactions.append({
                    "date": date_str,
                    "description": description,
                    "amount": amount,
                    "merchant": _extract_merchant(description),
                })
        except ValueError:
            pass

    # If we found transactions with the structured format, return them
    if transactions:
        return transactions

    # 2. If no specific format matched, fall back to line-by-line parsing
    # for common bank statement patterns.
    cr_dr_pattern = r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,.]+)\s+(Cr|Dr|CR|DR|cr|dr)\s*$'
    simple_pattern = r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\s+(.+?)\s+\$?([\-+]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$'
    three_col_pattern = r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s*$'

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            # Try CR/DR pattern (e.g., "01/01/2023 Grocery 50.00 DR")
            match = re.search(cr_dr_pattern, line)
            if match:
                date_str = match.group(1)
                desc = match.group(2).strip()
                amount_str = match.group(3)
                cr_dr = match.group(4).upper()
                
                amount = float(amount_str.replace(',', ''))
                if cr_dr == 'DR':
                    amount = -amount
                transactions.append({
                    "date": date_str, "description": desc,
                    "amount": amount, "merchant": _extract_merchant(desc)
                })
                continue
                
            # Try 3-column pattern (e.g., Date, Desc, Withdrawal, Deposit, Balance)
            # This requires all 3 numbers to be present on the line
            match = re.search(three_col_pattern, line)
            if match:
                date_str = match.group(1)
                desc = match.group(2).strip()
                col1 = float(match.group(3).replace(',', ''))
                col2 = float(match.group(4).replace(',', ''))
                # group 5 is balance, ignore
                
                # Usually col1 is withdrawal, col2 is deposit. If one is 0, use the other.
                if col1 > 0 and col2 == 0:
                    amount = -col1
                elif col2 > 0 and col1 == 0:
                    amount = col2
                else:
                    amount = -col1 # Default assumption
                    
                transactions.append({
                    "date": date_str, "description": desc,
                    "amount": amount, "merchant": _extract_merchant(desc)
                })
                continue

            # Try Simple format (Date, Description, Amount)
            match = re.search(simple_pattern, line)
            if match:
                date_str = match.group(1)
                desc = match.group(2).strip()
                amount_str = match.group(3)
                amount = float(amount_str.replace(',', ''))
                transactions.append({
                    "date": date_str, "description": desc,
                    "amount": amount, "merchant": _extract_merchant(desc)
                })
                continue
                
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


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

def process_document(file_path: str, password: Optional[str] = None) -> dict:
    """Full pipeline: extract text, parse transactions, return structured data.

    Parameters:
        file_path: Path to the PDF or text file on disk.
        password:  Optional password for encrypted PDFs.  Never stored.
    """
    if file_path.lower().endswith(('.md', '.txt')):
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        pdf_data = {
            "raw_text": raw_text,
            "page_count": 1,
            "tables": []
        }
    elif file_path.lower().endswith(('.xls', '.xlsx')):
        try:
            import pandas as pd
            # Read all sheets into a dictionary
            dfs = pd.read_excel(file_path, sheet_name=None)
            
            tables_data = []
            raw_text_parts = []
            
            # Convert each sheet into a list of lists format similar to pdfplumber's extract_tables
            for sheet_name, df in dfs.items():
                # Fill NaNs with empty strings to prevent parsing errors downstream
                df = df.fillna("")
                
                # Get the headers
                header = df.columns.tolist()
                
                # Get the rows
                rows = df.values.tolist()
                
                table_data = [header] + rows
                
                tables_data.append({
                    "page_num": len(tables_data) + 1,
                    "data": table_data
                })
                
                # Create a crude text representation of the sheet too
                raw_text_parts.append(f"--- Sheet: {sheet_name} ---")
                raw_text_parts.append("\t".join([str(h) for h in header]))
                for row in rows:
                    raw_text_parts.append("\t".join([str(cell) for cell in row]))
            
            pdf_data = {
                "raw_text": "\n".join(raw_text_parts),
                "page_count": len(tables_data),
                "tables": tables_data
            }
        except ImportError:
            raise ValueError("pandas and xlrd/openpyxl are required to process Excel files.")
    else:
        pdf_data = extract_text_from_pdf(file_path, password=password)

    # Extract from text
    text_transactions = extract_transactions_from_text(pdf_data.get("raw_text", ""))

    # Extract from tables
    table_transactions = extract_transactions_from_tables(pdf_data.get("tables", []))

    # Merge and deduplicate
    combined = text_transactions + table_transactions
    
    # Deduplicate based on date, description, and amount
    # Use a set to track seen transactions
    seen = set()
    all_transactions = []
    
    for txn in combined:
        # Create a unique signature for the transaction
        # description is lowered and stripped to handle minor parsing differences
        sig = (txn.get("date"), txn.get("description", "").lower().strip(), txn.get("amount"))
        if sig not in seen:
            seen.add(sig)
            all_transactions.append(txn)

    return {
        "raw_text": pdf_data.get("raw_text", ""),
        "page_count": pdf_data.get("page_count", 0),
        "transactions": all_transactions,
        "transaction_count": len(all_transactions),
    }

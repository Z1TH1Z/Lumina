"""
Direct ingestion script for HDFC bank statement transactions.
Reads all transactions from the XLS file, categorizes them properly,
and inserts into the SQLite database with correct INR currency.
Also creates synthetic transactions for categories not in the statement.
"""

import sqlite3
import sys
import re
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── Configuration ────────────────────────────────────────────────────────────
DB_PATH = "data/fincopilot.db"
XLS_PATH = "../Data/Acct_Statement_XXXXXXXX4451_05032026.xls"
USER_ID = 4
TXN_START_ROW = 22  # First data row in XLS

# ── Import categorizer ────────────────────────────────────────────────────────
from app.services.categorization import classify_transaction

# ── Read XLS ─────────────────────────────────────────────────────────────────

def read_xls_transactions(path: str) -> list[dict]:
    import xlrd
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    transactions = []
    for i in range(TXN_START_ROW, ws.nrows):
        date_str = str(ws.cell_value(i, 0)).strip()
        if not date_str or not re.match(r"\d{2}/\d{2}/\d{2}", date_str):
            continue
        narration = str(ws.cell_value(i, 1)).strip()
        ref_no    = str(ws.cell_value(i, 2)).strip()
        withdrawal_raw = ws.cell_value(i, 4)
        deposit_raw    = ws.cell_value(i, 5)

        try:
            withdrawal = float(str(withdrawal_raw).replace(",", "")) if withdrawal_raw else 0.0
            deposit    = float(str(deposit_raw).replace(",", "")) if deposit_raw else 0.0
        except ValueError:
            continue

        if withdrawal == 0.0 and deposit == 0.0:
            continue

        # Positive = credit/income, negative = debit/expense
        amount = deposit if deposit > 0 else -withdrawal

        # Parse DD/MM/YY
        try:
            d, m, y = date_str.split("/")
            txn_date = date(2000 + int(y), int(m), int(d))
        except Exception:
            continue

        merchant = _extract_merchant(narration)
        transactions.append({
            "date": txn_date.isoformat(),
            "description": narration,
            "merchant": merchant,
            "amount": amount,
            "currency": "INR",
            "ref_no": ref_no,
        })
    return transactions


def _extract_merchant(desc: str) -> str:
    """Pull a clean merchant name from an HDFC UPI narration."""
    desc_clean = re.sub(
        r'^(UPI|NEFT|IMPS|RTGS|NACH|ATM|POS|ACH)[- /]*', '', desc, flags=re.IGNORECASE
    )
    # For UPI: "MERCHANT NAME-upi_id@bank-IFSC-refno-UPI"
    # Take the part before the first @
    part = desc_clean.split("-")[0].strip() if "-" in desc_clean else desc_clean
    # Clean up
    words = [w for w in part.split() if len(w) > 1 and not re.match(r'^\d+$', w)][:3]
    return " ".join(words).lower().strip() or desc_clean[:30].lower()


# ── Synthetic transactions ────────────────────────────────────────────────────

SYNTHETIC = [
    # ── Salary / Income ──────────────────────────────────────────────────────
    ("2025-04-30", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY APR 2025", "techcorp solutions",  75000.0,  "income"),
    ("2025-05-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY MAY 2025", "techcorp solutions",  75000.0,  "income"),
    ("2025-06-30", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY JUN 2025", "techcorp solutions",  75000.0,  "income"),
    ("2025-07-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY JUL 2025", "techcorp solutions",  78000.0,  "income"),
    ("2025-08-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY AUG 2025", "techcorp solutions",  78000.0,  "income"),
    ("2025-09-30", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY SEP 2025", "techcorp solutions",  78000.0,  "income"),
    ("2025-10-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY OCT 2025", "techcorp solutions",  78000.0,  "income"),
    ("2025-11-30", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY NOV 2025", "techcorp solutions",  82000.0,  "income"),
    ("2025-12-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY DEC 2025 + BONUS", "techcorp solutions", 120000.0, "income"),
    ("2026-01-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY JAN 2026", "techcorp solutions",  82000.0,  "income"),
    ("2026-02-28", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY FEB 2026", "techcorp solutions",  82000.0,  "income"),
    ("2026-03-31", "NEFT-TECHCORP SOLUTIONS PVT LTD-SALARY MAR 2026", "techcorp solutions",  82000.0,  "income"),
    ("2025-07-15", "INT PAID-HDFC SAVINGS ACCOUNT INTEREST Q1", "hdfc bank",                  312.50, "income"),
    ("2025-10-15", "INT PAID-HDFC SAVINGS ACCOUNT INTEREST Q2", "hdfc bank",                  298.75, "income"),
    ("2026-01-15", "INT PAID-HDFC SAVINGS ACCOUNT INTEREST Q3", "hdfc bank",                  327.00, "income"),

    # ── Rent & Housing ────────────────────────────────────────────────────────
    ("2025-04-05", "NEFT-KRISHNA PROPERTY MGMT-RENT APR 2025", "krishna property", -14000.0, "housing"),
    ("2025-05-05", "NEFT-KRISHNA PROPERTY MGMT-RENT MAY 2025", "krishna property", -14000.0, "housing"),
    ("2025-06-05", "NEFT-KRISHNA PROPERTY MGMT-RENT JUN 2025", "krishna property", -14000.0, "housing"),
    ("2025-07-05", "NEFT-KRISHNA PROPERTY MGMT-RENT JUL 2025", "krishna property", -14000.0, "housing"),
    ("2025-08-05", "NEFT-KRISHNA PROPERTY MGMT-RENT AUG 2025", "krishna property", -14000.0, "housing"),
    ("2025-09-05", "NEFT-KRISHNA PROPERTY MGMT-RENT SEP 2025", "krishna property", -14000.0, "housing"),
    ("2025-10-05", "NEFT-KRISHNA PROPERTY MGMT-RENT OCT 2025", "krishna property", -14000.0, "housing"),
    ("2025-11-05", "NEFT-KRISHNA PROPERTY MGMT-RENT NOV 2025", "krishna property", -14000.0, "housing"),
    ("2025-12-05", "NEFT-KRISHNA PROPERTY MGMT-RENT DEC 2025", "krishna property", -14000.0, "housing"),
    ("2026-01-05", "NEFT-KRISHNA PROPERTY MGMT-RENT JAN 2026", "krishna property", -14000.0, "housing"),
    ("2026-02-05", "NEFT-KRISHNA PROPERTY MGMT-RENT FEB 2026", "krishna property", -14000.0, "housing"),
    ("2026-03-05", "NEFT-KRISHNA PROPERTY MGMT-RENT MAR 2026", "krishna property", -14000.0, "housing"),

    # ── Food / Swiggy / Zomato ────────────────────────────────────────────────
    ("2025-04-08", "UPI-SWIGGY-SWIGGY.10234@AXISBANK-UTIB0001234-ORDER123-UPI", "swiggy",     -245.0, "food"),
    ("2025-04-15", "UPI-ZOMATO-ZOMATO.PAY@AXISBANK-UTIB0001234-ORDER456-UPI",  "zomato",     -189.0, "food"),
    ("2025-05-02", "UPI-SWIGGY-SWIGGY.10234@AXISBANK-UTIB0001234-ORDER789-UPI", "swiggy",    -312.0, "food"),
    ("2025-05-20", "UPI-ZOMATO-ZOMATO.PAY@AXISBANK-UTIB0001234-ORDER012-UPI",  "zomato",     -425.0, "food"),
    ("2025-06-12", "UPI-BLINKIT-BLINKIT.ORDERS@AXISBANK-ORDER345-UPI",         "blinkit",    -567.0, "food"),
    ("2025-07-03", "UPI-SWIGGY INSTAMART-GROCERY567@SBIN-ORDER678-UPI",        "swiggy",     -890.0, "food"),
    ("2025-08-18", "UPI-DOMINOS PIZZA-PIZZA.INDIA@HDFC-ORDER901-UPI",          "dominos",    -478.0, "food"),
    ("2025-09-25", "UPI-KFC INDIA-KFC.ORDERS@AXIS-ORDER234-UPI",               "kfc",        -342.0, "food"),
    ("2025-10-10", "UPI-ZOMATO-ZOMATO.PAY@AXISBANK-ORDER567-UPI",             "zomato",     -198.0, "food"),

    # ── Transport / Fuel ──────────────────────────────────────────────────────
    ("2025-04-12", "UPI-UBER INDIA-UBER.INDIA@HDFCBANK-TRIP123-UPI",          "uber",       -189.0, "transport"),
    ("2025-05-07", "UPI-OLA CABS-OLACABS.PAY@SBI-TRIP456-UPI",               "ola",        -142.0, "transport"),
    ("2025-06-20", "UPI-HP PETROL PUMP-HP.FUEL@ICICI-FUEL789-UPI",           "hp petrol",  -2800.0, "transport"),
    ("2025-07-14", "UPI-FASTTAG RECHARGE-NHAI.TAG@HDFC-TOLL012-UPI",         "fasttag",    -500.0,  "transport"),
    ("2025-08-03", "UPI-RAPIDO BIKE-RAPIDO@PAYTM-TRIP345-UPI",               "rapido",     -67.0,   "transport"),
    ("2025-09-11", "UPI-IOCL FUEL STATION-IOCL.PAY@SBI-FUEL678-UPI",        "iocl",       -3200.0, "transport"),
    ("2025-10-28", "UPI-UBER INDIA-UBER.INDIA@HDFCBANK-TRIP901-UPI",         "uber",       -234.0,  "transport"),
    ("2025-11-15", "UPI-OLA CABS-OLACABS.PAY@SBI-TRIP234-UPI",              "ola",        -178.0,  "transport"),

    # ── Utilities ──────────────────────────────────────────────────────────────
    ("2025-04-20", "UPI-TANGEDCO ELECTRICITY-TNEB.BILL@SBI-EBILL123-UPI",   "tangedco",   -1245.0, "utilities"),
    ("2025-05-22", "UPI-TANGEDCO ELECTRICITY-TNEB.BILL@SBI-EBILL456-UPI",   "tangedco",   -1180.0, "utilities"),
    ("2025-06-21", "UPI-TANGEDCO ELECTRICITY-TNEB.BILL@SBI-EBILL789-UPI",   "tangedco",   -1560.0, "utilities"),
    ("2025-07-20", "UPI-TANGEDCO ELECTRICITY-TNEB.BILL@SBI-EBILL012-UPI",   "tangedco",   -1890.0, "utilities"),
    ("2025-04-10", "UPI-JIO RECHARGE-JIO.PAY@JIOMONEY-RECH123-UPI",         "jio",        -299.0,  "utilities"),
    ("2025-05-10", "UPI-JIO RECHARGE-JIO.PAY@JIOMONEY-RECH456-UPI",         "jio",        -299.0,  "utilities"),
    ("2025-06-10", "UPI-JIO RECHARGE-JIO.PAY@JIOMONEY-RECH789-UPI",         "jio",        -299.0,  "utilities"),
    ("2025-07-10", "UPI-AIRTEL BROADBAND-AIRTEL.BILL@AXIS-BBAND123-UPI",    "airtel",     -999.0,  "utilities"),
    ("2025-08-10", "UPI-AIRTEL BROADBAND-AIRTEL.BILL@AXIS-BBAND456-UPI",    "airtel",     -999.0,  "utilities"),

    # ── Entertainment / Streaming ─────────────────────────────────────────────
    ("2025-04-18", "UPI-NETFLIX INDIA-NETFLIX.INDIA@HDFC-SUB123-UPI",       "netflix",    -649.0,  "entertainment"),
    ("2025-05-18", "UPI-NETFLIX INDIA-NETFLIX.INDIA@HDFC-SUB456-UPI",       "netflix",    -649.0,  "entertainment"),
    ("2025-06-18", "UPI-NETFLIX INDIA-NETFLIX.INDIA@HDFC-SUB789-UPI",       "netflix",    -649.0,  "entertainment"),
    ("2025-04-25", "UPI-SPOTIFY INDIA-SPOTIFY@AXIS-MUSIC123-UPI",           "spotify",    -119.0,  "entertainment"),
    ("2025-05-25", "UPI-SPOTIFY INDIA-SPOTIFY@AXIS-MUSIC456-UPI",           "spotify",    -119.0,  "entertainment"),
    ("2025-04-30", "UPI-BOOKMYSHOW-BMS.TICKETS@HDFC-MOVIE123-UPI",         "bookmyshow", -420.0,  "entertainment"),
    ("2025-07-20", "UPI-PVR CINEMAS-PVR.PAY@SBI-CINEMA456-UPI",            "pvr",        -560.0,  "entertainment"),
    ("2025-10-05", "UPI-HOTSTAR DISNEY-HOTSTAR@AXIS-STREAM789-UPI",         "hotstar",    -299.0,  "entertainment"),

    # ── Healthcare ────────────────────────────────────────────────────────────
    ("2025-05-14", "UPI-APOLLO PHARMACY-APOLLO.MED@HDFC-MED123-UPI",       "apollo pharmacy", -876.0, "healthcare"),
    ("2025-08-22", "UPI-MEDPLUS PHARMACY-MEDPLUS@SBI-MED456-UPI",          "medplus",    -432.0,  "healthcare"),
    ("2025-11-08", "UPI-NETMEDS INDIA-NETMEDS.PAY@AXIS-MED789-UPI",       "netmeds",    -654.0,  "healthcare"),
    ("2025-09-15", "UPI-DR KRISHNA CLINIC-CLINIC@HDFC-DOC123-UPI",        "dr krishna", -500.0,  "healthcare"),
    ("2025-12-03", "UPI-APOLLO DIAGNOSTICS-APDX@SBI-DIAG456-UPI",         "apollo diagnostics", -1800.0, "healthcare"),

    # ── Insurance ─────────────────────────────────────────────────────────────
    ("2025-07-01", "NACH-LIC OF INDIA-PREMIUM DEBIT-LIFE INS POL", "lic india",          -4500.0, "insurance"),
    ("2025-10-01", "NACH-LIC OF INDIA-PREMIUM DEBIT-LIFE INS POL", "lic india",          -4500.0, "insurance"),
    ("2026-01-01", "NACH-LIC OF INDIA-PREMIUM DEBIT-LIFE INS POL", "lic india",          -4500.0, "insurance"),
    ("2025-06-15", "UPI-HDFC ERGO-HEALTH INSURANCE PREMIUM-2025",   "hdfc ergo",         -8200.0, "insurance"),
    ("2025-08-10", "UPI-BAJAJ ALLIANZ-VEHICLE INSURANCE RENEWAL",  "bajaj allianz",      -6800.0, "insurance"),

    # ── Investment / Mutual Funds ─────────────────────────────────────────────
    ("2025-04-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND APR",     "zerodha",            -5000.0, "investment"),
    ("2025-05-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND MAY",     "zerodha",            -5000.0, "investment"),
    ("2025-06-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND JUN",     "zerodha",            -5000.0, "investment"),
    ("2025-07-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND JUL",     "zerodha",            -5000.0, "investment"),
    ("2025-08-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND AUG",     "zerodha",            -5000.0, "investment"),
    ("2025-09-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND SEP",     "zerodha",            -5000.0, "investment"),
    ("2025-10-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND OCT",     "zerodha",            -5000.0, "investment"),
    ("2025-11-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND NOV",     "zerodha",            -5000.0, "investment"),
    ("2025-12-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND DEC",     "zerodha",            -5000.0, "investment"),
    ("2026-01-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND JAN",     "zerodha",            -5000.0, "investment"),
    ("2026-02-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND FEB",     "zerodha",            -5000.0, "investment"),
    ("2026-03-07", "NACH-ZERODHA BROKING-SIP MUTUAL FUND MAR",     "zerodha",            -5000.0, "investment"),
    ("2025-06-30", "UPI-GROWW-MUTUAL FUND PURCHASE-NIPPON MF",     "groww",              -10000.0, "investment"),
    ("2025-12-30", "UPI-GROWW-MUTUAL FUND PURCHASE-PARAG MF",      "groww",              -15000.0, "investment"),
    ("2025-09-20", "UPI-UPSTOX PRO-EQUITY BUY INFY 10 SHARES",     "upstox",             -17840.0, "investment"),

    # ── Shopping / E-commerce ─────────────────────────────────────────────────
    ("2025-04-14", "UPI-AMAZON INDIA-AMAZON.PAY@AMAZONPAY-ORDER123-UPI",   "amazon",    -1299.0, "shopping"),
    ("2025-05-22", "UPI-FLIPKART INTERNET-FKART@YESBANK-ORDER456-UPI",     "flipkart",  -2549.0, "shopping"),
    ("2025-06-05", "UPI-MYNTRA DESIGNS-MYNTRA@YESBANK-ORDER789-UPI",       "myntra",    -1890.0, "shopping"),
    ("2025-07-18", "UPI-AMAZON INDIA-AMAZON.PAY@AMAZONPAY-ORDER012-UPI",  "amazon",    -3450.0, "shopping"),
    ("2025-08-15", "UPI-CROMA STORES-CROMA.PAY@HDFC-ELEC345-UPI",         "croma",     -5999.0, "shopping"),
    ("2025-09-01", "UPI-NYKAA FASHION-NYKAA.PAY@AXIS-ORDER678-UPI",       "nykaa",     -1245.0, "shopping"),

    # ── Education ─────────────────────────────────────────────────────────────
    ("2025-06-01", "UPI-UDEMY ONLINE-UDEMY.IN@PAYPAL-COURSE123-UPI",      "udemy",      -1299.0, "education"),
    ("2025-08-01", "UPI-COURSERA INC-COURSERA@PAYPAL-COURSE456-UPI",      "coursera",   -2500.0, "education"),
    ("2025-11-01", "NEFT-UDEMY INDIA-ANNUAL SUBSCRIPTION",                "udemy",      -4999.0, "education"),

    # ── ATM Withdrawals ───────────────────────────────────────────────────────
    ("2025-04-17", "ATM CASH WITHDRAWAL-HDFC ATM T NAGAR CHENNAI",        "hdfc atm",  -3000.0, "cash"),
    ("2025-06-08", "ATM CASH WITHDRAWAL-HDFC ATM PERUNGUDI CHENNAI",      "hdfc atm",  -5000.0, "cash"),
    ("2025-08-25", "ATM CASH WITHDRAWAL-ICICI ATM OMR CHENNAI",           "icici atm", -2000.0, "cash"),
    ("2025-11-12", "ATM CASH WITHDRAWAL-SBI ATM VELACHERY CHENNAI",       "sbi atm",   -4000.0, "cash"),
]


# ── Database helpers ──────────────────────────────────────────────────────────

def get_existing_descriptions(conn: sqlite3.Connection, user_id: int) -> set[str]:
    cur = conn.cursor()
    cur.execute("SELECT description FROM transactions WHERE user_id = ?", (user_id,))
    return {row[0] for row in cur.fetchall()}


def insert_transactions(conn: sqlite3.Connection, rows: list[dict]):
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO transactions
           (user_id, date, description, merchant, amount, currency,
            category, category_confidence, is_anomaly, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))""",
        [
            (
                r["user_id"], r["date"], r["description"], r["merchant"],
                r["amount"], r["currency"], r["category"], r["confidence"],
            )
            for r in rows
        ],
    )
    conn.commit()
    return cur.rowcount


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)

    # ── Step 1: Read real bank statement transactions ─────────────────────────
    print("Reading XLS bank statement…")
    real_txns = read_xls_transactions(XLS_PATH)
    print(f"  Found {len(real_txns)} transactions in XLS")

    existing = get_existing_descriptions(conn, USER_ID)
    print(f"  Existing in DB for user {USER_ID}: {len(existing)}")

    # ── Step 2: Delete old transactions to re-ingest cleanly ─────────────────
    print("Clearing existing transactions for user (re-ingesting with correct INR currency)…")
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE user_id = ?", (USER_ID,))
    conn.commit()
    print(f"  Removed {cur.rowcount} old rows")

    # ── Step 3: Categorise & prepare real transactions ───────────────────────
    print("Categorising real transactions…")
    to_insert = []
    category_counts: dict[str, int] = {}

    for txn in real_txns:
        result = classify_transaction(txn["description"], txn["merchant"], txn["amount"])
        cat   = result["category"]
        conf  = result["confidence"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        to_insert.append({
            "user_id":    USER_ID,
            "date":       txn["date"],
            "description": txn["description"],
            "merchant":   txn["merchant"],
            "amount":     txn["amount"],
            "currency":   "INR",
            "category":   cat,
            "confidence": conf,
        })

    print(f"  Real transactions by category: {category_counts}")

    # ── Step 4: Prepare synthetic transactions ────────────────────────────────
    print("Adding synthetic transactions…")
    synth_inserted = 0
    for entry in SYNTHETIC:
        date_str, desc, merchant, amount, forced_cat = entry
        result = classify_transaction(desc, merchant, amount)
        # If rule engine agrees with forced category, use its confidence; else force
        cat  = result["category"] if result["category"] == forced_cat else forced_cat
        conf = result["confidence"] if cat == result["category"] else 0.85
        to_insert.append({
            "user_id":     USER_ID,
            "date":        date_str,
            "description": desc,
            "merchant":    merchant,
            "amount":      float(amount),
            "currency":    "INR",
            "category":    cat,
            "confidence":  conf,
        })
        synth_inserted += 1

    # ── Step 5: Insert everything ─────────────────────────────────────────────
    inserted = insert_transactions(conn, to_insert)
    conn.close()

    total_real  = len(real_txns)
    total_synth = synth_inserted

    print("\n" + "=" * 60)
    print("  Lumina Ingestion Complete")
    print("=" * 60)
    print(f"  Real bank statement transactions : {total_real}")
    print(f"  Synthetic (supplementary) txns  : {total_synth}")
    print(f"  Total rows inserted             : {inserted}")
    print(f"  User                            : Nithin Kotala (ID {USER_ID})")
    print(f"  Currency                        : INR")
    print("=" * 60)

    # ── Step 6: Summary by category ──────────────────────────────────────────
    conn2 = sqlite3.connect(DB_PATH)
    cur2  = conn2.cursor()
    cur2.execute(
        "SELECT category, count(*), round(sum(amount),2) "
        "FROM transactions WHERE user_id = ? "
        "GROUP BY category ORDER BY count(*) DESC",
        (USER_ID,),
    )
    print("\n  Category breakdown:")
    print(f"  {'Category':<18} {'Count':>6}  {'Net Amount (INR)':>18}")
    print(f"  {'-'*18} {'-'*6}  {'-'*18}")
    for row in cur2.fetchall():
        print(f"  {row[0]:<18} {row[1]:>6}  {row[2]:>18,.2f}")
    conn2.close()


if __name__ == "__main__":
    main()

"""
Train the transaction categorization model.

Usage:
    cd backend
    python -m app.ml.train_categorizer

Outputs:
    ./models/categorizer.pkl  — loaded by ml_service.MLService

The model uses a hybrid feature matrix:
    - TF-IDF on cleaned description text
    - Structured numeric features (amount, day_of_week, is_debit, etc.)
combined via scipy.sparse.hstack, then fed to a RandomForestClassifier
with class_weight="balanced" to handle the natural imbalance across
spending categories.
"""

import pickle
import os
import sys
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Labeled training dataset
# Entries: (description, merchant, amount, category)
# Covers Indian + global transaction patterns across all categories.
# ---------------------------------------------------------------------------
TRAINING_DATA: list[tuple[str, str, float, str]] = [
    # income
    ("SALARY CREDIT APR", "employer", 85000.0, "income"),
    ("PAYROLL DEPOSIT", "company payroll", 5200.0, "income"),
    ("NEFT CR SALARY HDFC", "hdfc", 62000.0, "income"),
    ("INTEREST CREDITED SB", "bank", 420.0, "income"),
    ("DIVIDEND CREDIT INFY", "infosys", 3200.0, "income"),
    ("CASHBACK CREDIT", "bank rewards", 150.0, "income"),
    ("REFUND FLIPKART ORDER", "flipkart", 899.0, "income"),
    ("REVERSAL CHARGE", "bank", 50.0, "income"),
    ("STIPEND PAYMENT", "internship", 15000.0, "income"),
    ("FREELANCE PAYMENT RECEIVED", "client", 25000.0, "income"),
    ("BONUS CREDIT", "employer", 20000.0, "income"),
    ("TAX REFUND INCOME TAX DEPT", "it dept", 8500.0, "income"),

    # food
    ("SWIGGY ORDER 38291", "swiggy", -450.0, "food"),
    ("ZOMATO ORDER DINNER", "zomato", -389.0, "food"),
    ("BLINKIT GROCERY DELIVERY", "blinkit", -820.0, "food"),
    ("ZEPTO INSTANT DELIVERY", "zepto", -340.0, "food"),
    ("DUNZO DELIVERY", "dunzo", -180.0, "food"),
    ("MCDONALDS KORAMANGALA", "mcdonalds", -350.0, "food"),
    ("DOMINOS PIZZA ORDER", "dominos", -649.0, "food"),
    ("BURGER KING UPI", "burger king", -289.0, "food"),
    ("STARBUCKS COFFEE", "starbucks", -480.0, "food"),
    ("CHAAYOS TEA OUTLET", "chaayos", -120.0, "food"),
    ("DMART GROCERY PURCHASE", "dmart", -2340.0, "food"),
    ("BIG BAZAAR SHOPPING", "big bazaar", -1850.0, "food"),
    ("RELIANCE FRESH PURCHASE", "reliance fresh", -760.0, "food"),
    ("RESTAURANT BILL DINING", "local restaurant", -680.0, "food"),
    ("PIZZA HUT ORDER", "pizza hut", -580.0, "food"),
    ("KFC CHICKEN BUCKET", "kfc", -499.0, "food"),
    ("SUBWAY SANDWICH", "subway", -329.0, "food"),
    ("UBEREATS ORDER", "ubereats", -520.0, "food"),
    ("DOORDASH DELIVERY", "doordash", -38.0, "food"),
    ("WHOLE FOODS GROCERY", "whole foods", -87.0, "food"),
    ("KROGER SUPERMARKET", "kroger", -65.0, "food"),
    ("TRADER JOE GROCERY", "trader joe", -54.0, "food"),
    ("CAFE COFFEE DAY", "ccd", -210.0, "food"),
    ("BARISTA COFFEE", "barista", -190.0, "food"),
    ("INSTAMART PURCHASE", "swiggy instamart", -920.0, "food"),

    # transport
    ("UBER RIDE UPI", "uber", -220.0, "transport"),
    ("OLA CABS BOOKING", "ola", -180.0, "transport"),
    ("RAPIDO BIKE TAXI", "rapido", -65.0, "transport"),
    ("IRCTC TRAIN TICKET", "irctc", -1200.0, "transport"),
    ("INDIGO AIRLINES BOOKING", "indigo", -4500.0, "transport"),
    ("AIR INDIA FLIGHT", "air india", -6800.0, "transport"),
    ("MAKEMYTRIP FLIGHT BOOKING", "makemytrip", -8200.0, "transport"),
    ("GOIBIBO BUS TICKET", "goibibo", -650.0, "transport"),
    ("REDBUS TICKET BOOKING", "redbus", -750.0, "transport"),
    ("FASTAG RECHARGE", "fastag", -500.0, "transport"),
    ("DMRC METRO RECHARGE", "dmrc", -200.0, "transport"),
    ("PETROL PUMP IOCL", "iocl", -3200.0, "transport"),
    ("BPCL FUEL FILL", "bpcl", -2800.0, "transport"),
    ("HP PETROL STATION", "hp pump", -4100.0, "transport"),
    ("SHELL FUEL", "shell", -52.0, "transport"),
    ("PARKING CHARGE MALL", "parking", -80.0, "transport"),
    ("LYFT RIDE", "lyft", -18.0, "transport"),
    ("TOLL PAYMENT", "toll", -150.0, "transport"),
    ("SPICEJET TICKET", "spicejet", -3200.0, "transport"),

    # utilities
    ("BESCOM ELECTRICITY BILL", "bescom", -1850.0, "utilities"),
    ("MSEDCL ELECTRICITY PAYMENT", "msedcl", -2200.0, "utilities"),
    ("TATA POWER BILL PAYMENT", "tata power", -1600.0, "utilities"),
    ("JIO RECHARGE 599", "jio", -599.0, "utilities"),
    ("AIRTEL POSTPAID BILL", "airtel", -799.0, "utilities"),
    ("BSNL BROADBAND BILL", "bsnl", -599.0, "utilities"),
    ("VODAFONE VI BILL", "vodafone", -499.0, "utilities"),
    ("TATA SKY DTH RECHARGE", "tata sky", -399.0, "utilities"),
    ("DISH TV RECHARGE", "dish tv", -350.0, "utilities"),
    ("WATER BILL BWSSB", "bwssb", -400.0, "utilities"),
    ("FIBER BROADBAND BILL", "act fibernet", -999.0, "utilities"),
    ("VERIZON WIRELESS BILL", "verizon", -85.0, "utilities"),
    ("COMCAST INTERNET", "comcast", -79.0, "utilities"),
    ("ATT PHONE BILL", "at&t", -95.0, "utilities"),
    ("SPECTRUM CABLE BILL", "spectrum", -110.0, "utilities"),

    # entertainment
    ("NETFLIX SUBSCRIPTION", "netflix", -649.0, "entertainment"),
    ("SPOTIFY PREMIUM", "spotify", -119.0, "entertainment"),
    ("HOTSTAR SUBSCRIPTION", "hotstar", -899.0, "entertainment"),
    ("PRIME VIDEO SUBSCRIPTION", "amazon prime", -1499.0, "entertainment"),
    ("JIOCINEMA PREMIUM", "jiocinema", -999.0, "entertainment"),
    ("SONYLIV PREMIUM", "sonyliv", -599.0, "entertainment"),
    ("ZEE5 SUBSCRIPTION", "zee5", -499.0, "entertainment"),
    ("YOUTUBE PREMIUM", "youtube premium", -189.0, "entertainment"),
    ("BOOKMYSHOW MOVIE TICKET", "bookmyshow", -600.0, "entertainment"),
    ("PVR CINEMAS TICKET", "pvr", -450.0, "entertainment"),
    ("INOX MOVIE TICKET", "inox", -420.0, "entertainment"),
    ("STEAM GAME PURCHASE", "steam", -999.0, "entertainment"),
    ("PLAYSTATION STORE", "playstation", -4999.0, "entertainment"),
    ("XBOX GAME PASS", "xbox", -699.0, "entertainment"),
    ("HULU SUBSCRIPTION", "hulu", -18.0, "entertainment"),
    ("DISNEY PLUS", "disney", -14.0, "entertainment"),
    ("TWITCH SUBSCRIPTION", "twitch", -5.0, "entertainment"),
    ("CONCERT TICKET PURCHASE", "event", -2500.0, "entertainment"),
    ("APPLE TV PLUS", "apple", -99.0, "entertainment"),

    # healthcare
    ("APOLLO PHARMACY MEDICINE", "apollo pharmacy", -850.0, "healthcare"),
    ("MEDPLUS CHEMIST", "medplus", -620.0, "healthcare"),
    ("NETMEDS ORDER", "netmeds", -480.0, "healthcare"),
    ("1MG MEDICINE DELIVERY", "1mg", -720.0, "healthcare"),
    ("PHARMEASY ORDER", "pharmeasy", -560.0, "healthcare"),
    ("DOCTOR CONSULTATION FEE", "clinic", -500.0, "healthcare"),
    ("PRACTO CONSULTATION", "practo", -800.0, "healthcare"),
    ("DENTAL CLINIC PAYMENT", "dental", -2500.0, "healthcare"),
    ("DIAGNOSTIC LAB TEST", "lab test", -1200.0, "healthcare"),
    ("HOSPITAL BILL PAYMENT", "hospital", -15000.0, "healthcare"),
    ("HEALTH INSURANCE PREMIUM", "star health", -12000.0, "healthcare"),
    ("MEDICLAIM PREMIUM", "niva bupa", -8500.0, "healthcare"),
    ("CVS PHARMACY", "cvs", -45.0, "healthcare"),
    ("WALGREENS PRESCRIPTION", "walgreens", -32.0, "healthcare"),
    ("OPTOMETRY VISIT", "eye clinic", -150.0, "healthcare"),

    # insurance
    ("LIC PREMIUM PAYMENT", "lic", -5000.0, "insurance"),
    ("HDFC LIFE PREMIUM", "hdfc life", -8000.0, "insurance"),
    ("ICICI PRU LIFE INSURANCE", "icici pru", -7500.0, "insurance"),
    ("CAR INSURANCE RENEWAL", "bajaj allianz", -12000.0, "insurance"),
    ("TWO WHEELER INSURANCE", "new india assurance", -3500.0, "insurance"),
    ("TERM INSURANCE PREMIUM", "max life", -15000.0, "insurance"),
    ("GEICO AUTO INSURANCE", "geico", -180.0, "insurance"),
    ("ALLSTATE INSURANCE", "allstate", -210.0, "insurance"),
    ("STATE FARM PREMIUM", "state farm", -195.0, "insurance"),
    ("PROGRESSIVE INSURANCE", "progressive", -165.0, "insurance"),

    # shopping
    ("AMAZON ORDER DELIVERED", "amazon", -1299.0, "shopping"),
    ("FLIPKART PURCHASE", "flipkart", -2499.0, "shopping"),
    ("MYNTRA CLOTHING ORDER", "myntra", -1799.0, "shopping"),
    ("MEESHO ORDER", "meesho", -599.0, "shopping"),
    ("AJIO FASHION PURCHASE", "ajio", -1299.0, "shopping"),
    ("NYKAA BEAUTY ORDER", "nykaa", -850.0, "shopping"),
    ("NIKE SHOES PURCHASE", "nike", -6999.0, "shopping"),
    ("ADIDAS APPAREL", "adidas", -3999.0, "shopping"),
    ("APPLE IPHONE PURCHASE", "apple", -79900.0, "shopping"),
    ("CROMA ELECTRONICS", "croma", -15000.0, "shopping"),
    ("VIJAY SALES TV PURCHASE", "vijay sales", -45000.0, "shopping"),
    ("RELIANCE DIGITAL STORE", "reliance digital", -12000.0, "shopping"),
    ("IKEA FURNITURE PURCHASE", "ikea", -8500.0, "shopping"),
    ("PEPPERFRY SOFA ORDER", "pepperfry", -25000.0, "shopping"),
    ("EBAY PURCHASE", "ebay", -75.0, "shopping"),
    ("BEST BUY ELECTRONICS", "best buy", -450.0, "shopping"),
    ("COSTCO MEMBERSHIP PURCHASE", "costco", -68.0, "shopping"),
    ("HOME DEPOT HARDWARE", "home depot", -95.0, "shopping"),
    ("WALMART SHOPPING", "walmart", -120.0, "shopping"),
    ("TARGET STORE PURCHASE", "target", -88.0, "shopping"),

    # investment
    ("ZERODHA EQUITY PURCHASE", "zerodha", -50000.0, "investment"),
    ("GROWW SIP MUTUAL FUND", "groww", -5000.0, "investment"),
    ("UPSTOX STOCK BUY", "upstox", -25000.0, "investment"),
    ("KUVERA MUTUAL FUND SIP", "kuvera", -3000.0, "investment"),
    ("SIP HDFC EQUITY FUND", "hdfc amc", -10000.0, "investment"),
    ("FIXED DEPOSIT BOOKING", "sbi", -100000.0, "investment"),
    ("PPF CONTRIBUTION", "post office ppf", -5000.0, "investment"),
    ("NPS CONTRIBUTION", "nps trust", -2000.0, "investment"),
    ("SOVEREIGN GOLD BOND", "rbi", -5000.0, "investment"),
    ("ROBINHOOD STOCK PURCHASE", "robinhood", -500.0, "investment"),
    ("FIDELITY INVESTMENT", "fidelity", -1000.0, "investment"),
    ("VANGUARD ETF PURCHASE", "vanguard", -2000.0, "investment"),
    ("SCHWAB BROKERAGE", "schwab", -800.0, "investment"),
    ("CRYPTO PURCHASE BITCOIN", "wazirx", -10000.0, "investment"),
    ("RECURRING DEPOSIT BOOKING", "axis bank", -2000.0, "investment"),

    # education
    ("UDEMY COURSE PURCHASE", "udemy", -499.0, "education"),
    ("COURSERA SUBSCRIPTION", "coursera", -2400.0, "education"),
    ("BYJUS SUBSCRIPTION PAYMENT", "byjus", -18000.0, "education"),
    ("UNACADEMY SUBSCRIPTION", "unacademy", -4999.0, "education"),
    ("VEDANTU CLASSES PAYMENT", "vedantu", -6000.0, "education"),
    ("UPGRAD COURSE FEE", "upgrad", -50000.0, "education"),
    ("SIMPLILEARN COURSE", "simplilearn", -15000.0, "education"),
    ("SCHOOL FEE PAYMENT", "school", -25000.0, "education"),
    ("COLLEGE TUITION FEE", "university", -80000.0, "education"),
    ("EXAM FEE PAYMENT", "exam board", -1000.0, "education"),
    ("STUDENT LOAN EMI", "bank emi", -8000.0, "education"),
    ("TEXTBOOK PURCHASE", "amazon books", -650.0, "education"),

    # transfer
    ("NEFT TO SAVINGS ACCOUNT", "self transfer", -50000.0, "transfer"),
    ("IMPS TO FRIEND SPLIT", "upi transfer", -1500.0, "transfer"),
    ("UPI TRANSFER SENT", "phonepe", -2000.0, "transfer"),
    ("ZELLE PAYMENT SENT", "zelle", -200.0, "transfer"),
    ("VENMO PAYMENT", "venmo", -45.0, "transfer"),
    ("PAYPAL MONEY SENT", "paypal", -100.0, "transfer"),
    ("WISE INTERNATIONAL TRANSFER", "wise", -15000.0, "transfer"),
    ("WIRE TRANSFER ABROAD", "bank wire", -25000.0, "transfer"),
    ("ACH PAYMENT", "ach", -500.0, "transfer"),
    ("FAMILY TRANSFER SENT", "rtgs", -30000.0, "transfer"),

    # housing
    ("RENT PAYMENT MARCH", "landlord", -22000.0, "housing"),
    ("HOUSE RENT UPI TRANSFER", "owner upi", -18000.0, "housing"),
    ("APARTMENT MAINTENANCE CHARGE", "society", -3500.0, "housing"),
    ("PROPERTY TAX PAYMENT", "municipal corp", -8000.0, "housing"),
    ("MORTGAGE EMI PAYMENT", "hdfc home loan", -35000.0, "housing"),
    ("HOA FEES PAYMENT", "hoa", -250.0, "housing"),
    ("LEASE PAYMENT", "landlord", -1500.0, "housing"),
    ("APARTMENT DEPOSIT", "rental agency", -50000.0, "housing"),

    # cash
    ("ATM CASH WITHDRAWAL SBI", "sbi atm", -5000.0, "cash"),
    ("ATM WDL HDFC BANK", "hdfc atm", -3000.0, "cash"),
    ("CASH WITHDRAWAL ICICI", "icici atm", -10000.0, "cash"),
    ("ATM TRANSACTION CHARGE", "atm", -20.0, "cash"),
    ("CASH WITHDRAWAL AXIS", "axis atm", -2000.0, "cash"),

    # other (catch-all for ambiguous)
    ("MISCELLANEOUS CHARGE", "unknown", -100.0, "other"),
    ("SERVICE CHARGE", "bank", -50.0, "other"),
    ("BANK PROCESSING FEE", "bank", -200.0, "other"),
    ("CONVENIENCE FEE", "portal", -25.0, "other"),
    ("MEMBERSHIP FEE ANNUAL", "club", -5000.0, "other"),

    # -----------------------------------------------------------------------
    # Additional training data: HDFC UPI narration patterns + more examples
    # per class to improve generalisation.
    # Descriptions mirror what clean_text() produces from real bank narrations.
    # -----------------------------------------------------------------------

    # income – HDFC UPI credit patterns
    ("UPI-SUNEETHA KOTALA-KOTALASUNEETHA@OKICICI", "suneetha kotala", 200.0, "income"),
    ("UPI-DIVYAM SAHU-DIVYAMSAHU2004@OKSBI", "divyam sahu", 500.0, "income"),
    ("NEFT CR BONUS Q4", "employer", 15000.0, "income"),
    ("SALARY APRIL CREDIT HDFC", "company", 72000.0, "income"),
    ("INT PD ON SAVINGS", "hdfc bank", 320.0, "income"),
    ("INTEREST CREDITED Q1", "bank", 180.0, "income"),
    ("CASHBACK RECEIVED PAYTM", "paytm", 50.0, "income"),
    ("REFUND AMAZON ORDER", "amazon", 399.0, "income"),
    ("REVERSAL TXN FEE", "bank", 18.0, "income"),
    ("DIVIDEND TATA MOTORS", "bse", 1200.0, "income"),
    ("STIPEND MAR INTERNSHIP", "startup", 12000.0, "income"),
    ("FREELANCE CREDIT CLIENT", "client upi", 18000.0, "income"),

    # food – HDFC UPI food delivery patterns
    ("UPI-SWIGGY-SWIGGY@AXISBANK", "swiggy", -340.0, "food"),
    ("UPI-ZOMATO-ZOMATO@ICICI", "zomato", -420.0, "food"),
    ("UPI-BLINKIT-BLINKIT@HDFC", "blinkit", -680.0, "food"),
    ("UPI-ZEPTO-ZEPTO@HDFC", "zepto", -290.0, "food"),
    ("UPI-MCDONALDS INDIA-MCD@HDFC", "mcdonalds", -399.0, "food"),
    ("UPI-DOMINOS-DOMINOS@ICICI", "dominos", -549.0, "food"),
    ("UPI-KFC INDIA-KFC@SBI", "kfc", -419.0, "food"),
    ("UPI-STARBUCKS-STARBUCKS@HDFC", "starbucks", -520.0, "food"),
    ("UPI-INSTAMART-SWIGGYINSTAMART@AXIS", "swiggy instamart", -870.0, "food"),
    ("UPI-DMART READY-DMARTREADY@HDFC", "dmart", -1840.0, "food"),
    ("GROCERY PURCHASE LOCAL STORE", "local", -560.0, "food"),
    ("RESTAURANT DINNER PAYMENT", "restaurant", -890.0, "food"),
    ("CAFE LUNCH BILL UPI", "cafe", -310.0, "food"),
    ("PIZZA ORDER ONLINE", "pizza hut", -640.0, "food"),
    ("DHABA ROADSIDE MEAL", "dhaba", -220.0, "food"),

    # transport – HDFC UPI transport patterns
    ("UPI-UBER INDIA-UBER@AXISBANK", "uber", -195.0, "transport"),
    ("UPI-OLA-OLA@ICICI", "ola", -160.0, "transport"),
    ("UPI-RAPIDO-RAPIDO@SBI", "rapido", -55.0, "transport"),
    ("UPI-IRCTC-IRCTC@HDFC", "irctc", -1450.0, "transport"),
    ("UPI-INDIGO-INDIGO@HDFC", "indigo", -3800.0, "transport"),
    ("UPI-REDBUS-REDBUS@ICICI", "redbus", -620.0, "transport"),
    ("UPI-MAKEMYTRIP-MMT@HDFC", "makemytrip", -7200.0, "transport"),
    ("FASTAG WALLET RECHARGE", "fastag", -500.0, "transport"),
    ("PETROL PUMP PAYMENT IOCL", "iocl", -2900.0, "transport"),
    ("HP PETROL STATION FILL", "hp pump", -3600.0, "transport"),
    ("BPCL FUEL PAYMENT", "bpcl", -2400.0, "transport"),
    ("PARKING CHARGES MALL", "parking", -60.0, "transport"),
    ("TOLL PLAZA PAYMENT", "toll", -130.0, "transport"),
    ("METRO CARD RECHARGE DMRC", "dmrc", -200.0, "transport"),
    ("AIR TICKET BOOKING VISTARA", "vistara", -5200.0, "transport"),

    # utilities – HDFC UPI utility patterns
    ("UPI-BESCOM-BESCOM@HDFC", "bescom", -1720.0, "utilities"),
    ("UPI-JIO-JIO@HDFC", "jio", -599.0, "utilities"),
    ("UPI-AIRTEL-AIRTEL@ICICI", "airtel", -799.0, "utilities"),
    ("UPI-TANGEDCO-TANGEDCO@SBI", "tangedco", -1250.0, "utilities"),
    ("UPI-TATAPOWER-TATAPOWER@HDFC", "tata power", -1480.0, "utilities"),
    ("ELECTRICITY BILL PAYMENT", "bescom", -1900.0, "utilities"),
    ("MOBILE RECHARGE AIRTEL", "airtel", -299.0, "utilities"),
    ("BROADBAND BILL ACT", "act fibernet", -999.0, "utilities"),
    ("WATER BILL PAYMENT BWSSB", "bwssb", -380.0, "utilities"),
    ("DTH RECHARGE TATA PLAY", "tata sky", -349.0, "utilities"),
    ("INTERNET BILL JIOFIBER", "jio", -699.0, "utilities"),
    ("PHONE BILL VODAFONE VI", "vodafone", -459.0, "utilities"),

    # entertainment – HDFC UPI + Google Play patterns
    ("UPI-NETFLIX-NETFLIX@HDFC", "netflix", -649.0, "entertainment"),
    ("UPI-SPOTIFY-SPOTIFY@AXIS", "spotify", -119.0, "entertainment"),
    ("UPI-GOOGLE PLAY-PLAYSTORE@AXISBANK", "google play", -99.0, "entertainment"),
    ("UPI-GOOGLE PLAY-PLAYSTORE@AXISBANK", "google play", -199.0, "entertainment"),
    ("UPI-GOOGLE PLAY-PLAYSTORE@AXIS", "google play", -49.0, "entertainment"),
    ("GOOGLE INDIA DIGITAL SUBSCRIPTION", "google", -129.0, "entertainment"),
    ("GOOGLE PLAY SUBSCRIPTION", "google play", -79.0, "entertainment"),
    ("UPI-HOTSTAR-HOTSTAR@ICICI", "hotstar", -899.0, "entertainment"),
    ("UPI-PVR CINEMAS-PVR@HDFC", "pvr", -480.0, "entertainment"),
    ("UPI-BOOKMYSHOW-BMS@ICICI", "bookmyshow", -600.0, "entertainment"),
    ("PRIME VIDEO SUBSCRIPTION APR", "amazon prime", -1499.0, "entertainment"),
    ("JIOCINEMA PREMIUM PLAN", "jiocinema", -999.0, "entertainment"),
    ("ZEE5 MONTHLY PLAN", "zee5", -499.0, "entertainment"),
    ("YOUTUBE PREMIUM MONTHLY", "youtube", -189.0, "entertainment"),
    ("STEAM WALLET TOPUP", "steam", -500.0, "entertainment"),
    ("INOX MOVIE TICKET BOOKING", "inox", -380.0, "entertainment"),
    ("SONYLIV ANNUAL PLAN", "sonyliv", -999.0, "entertainment"),

    # healthcare – HDFC UPI health patterns
    ("UPI-APOLLO PHARMACY-APOLLOPH@HDFC", "apollo pharmacy", -740.0, "healthcare"),
    ("UPI-MEDPLUS-MEDPLUS@SBI", "medplus", -560.0, "healthcare"),
    ("UPI-NETMEDS-NETMEDS@HDFC", "netmeds", -430.0, "healthcare"),
    ("UPI-1MG-ONEMG@HDFC", "1mg", -680.0, "healthcare"),
    ("UPI-PHARMEASY-PHARMEASY@ICICI", "pharmeasy", -520.0, "healthcare"),
    ("DOCTOR CONSULTATION PRACTO", "practo", -700.0, "healthcare"),
    ("HOSPITAL BILL PAYMENT OPD", "hospital", -2200.0, "healthcare"),
    ("DENTAL TREATMENT CLINIC", "dental", -3500.0, "healthcare"),
    ("DIAGNOSTIC LAB THYROCARE", "lab", -800.0, "healthcare"),
    ("HEALTHKART SUPPLEMENT ORDER", "healthkart", -1200.0, "healthcare"),
    ("MEDICINE PURCHASE PHARMACY", "pharmacy", -480.0, "healthcare"),
    ("LYBRATE DOCTOR CONSULT", "lybrate", -400.0, "healthcare"),

    # insurance – premium payment patterns
    ("UPI-LIC INDIA-LIC@SBI", "lic", -4800.0, "insurance"),
    ("UPI-HDFC LIFE-HDFCLIFE@HDFC", "hdfc life", -7800.0, "insurance"),
    ("UPI-ICICI PRU-ICICIPRU@ICICI", "icici pru", -6500.0, "insurance"),
    ("BAJAJ ALLIANZ CAR INSURANCE", "bajaj allianz", -11000.0, "insurance"),
    ("STAR HEALTH PREMIUM PAYMENT", "star health", -9800.0, "insurance"),
    ("NIVA BUPA MEDICLAIM RENEWAL", "niva bupa", -7200.0, "insurance"),
    ("TERM PLAN PREMIUM MAX LIFE", "max life", -14000.0, "insurance"),
    ("TWO WHEELER INSURANCE RENEW", "new india assurance", -3200.0, "insurance"),
    ("VEHICLE INSURANCE PAYMENT", "bajaj", -8500.0, "insurance"),
    ("ULIP PREMIUM PAYMENT", "hdfc life", -5000.0, "insurance"),

    # shopping – HDFC UPI e-commerce patterns
    ("UPI-AMAZON-AMAZON@HDFC", "amazon", -1499.0, "shopping"),
    ("UPI-FLIPKART-FLIPKART@YESB", "flipkart", -2199.0, "shopping"),
    ("UPI-MYNTRA-MYNTRA@ICICI", "myntra", -1599.0, "shopping"),
    ("UPI-MEESHO-MEESHO@AXIS", "meesho", -499.0, "shopping"),
    ("UPI-NYKAA-NYKAA@HDFC", "nykaa", -780.0, "shopping"),
    ("UPI-AJIO-AJIO@ICICI", "ajio", -1299.0, "shopping"),
    ("UPI-CROMA-CROMA@HDFC", "croma", -12000.0, "shopping"),
    ("UPI-NAVEEN STORES-NAVEEN@SBI", "naveen stores", -430.0, "shopping"),
    ("UPI-ALL MART-ALLMART@PAYTM", "all mart", -280.0, "shopping"),
    ("UPI-ENZO-GPAY@ICICI", "enzo", -640.0, "shopping"),
    ("RELIANCE DIGITAL PURCHASE", "reliance digital", -8500.0, "shopping"),
    ("VIJAY SALES ELECTRONICS", "vijay sales", -22000.0, "shopping"),
    ("ONLINE SHOPPING SNAPDEAL", "snapdeal", -850.0, "shopping"),
    ("CLOTHING PURCHASE ZARA", "zara", -3200.0, "shopping"),
    ("TATA CLIQ ORDER", "tata cliq", -1800.0, "shopping"),

    # investment – brokerage and fund patterns
    ("UPI-ZERODHA-ZERODHA@HDFC", "zerodha", -25000.0, "investment"),
    ("UPI-GROWW-GROWWBRK@HDFC", "groww", -5000.0, "investment"),
    ("UPI-GROWW INVEST TECH-GROWW@HDFC", "groww", -10000.0, "investment"),
    ("UPI-UPSTOX-UPSTOX@HDFC", "upstox", -15000.0, "investment"),
    ("UPI-KUVERA-KUVERA@ICICI", "kuvera", -3000.0, "investment"),
    ("MUTUAL FUND SIP AXIS", "axis amc", -2000.0, "investment"),
    ("SIP PAYMENT HDFC EQUITY", "hdfc amc", -5000.0, "investment"),
    ("FIXED DEPOSIT BOOKING HDFC", "hdfc bank", -50000.0, "investment"),
    ("PPF ANNUAL CONTRIBUTION", "post office", -10000.0, "investment"),
    ("NPS TIER1 CONTRIBUTION", "nps", -2000.0, "investment"),
    ("RECURRING DEPOSIT AXIS", "axis bank", -3000.0, "investment"),
    ("KFINTECH MUTUAL FUND", "kfintech", -4000.0, "investment"),
    ("CAMS MUTUAL FUND INVEST", "cams", -6000.0, "investment"),

    # education
    ("UPI-UDEMY-UDEMY@PAYTM", "udemy", -499.0, "education"),
    ("UPI-COURSERA-COURSERA@HDFC", "coursera", -1800.0, "education"),
    ("UPI-BYJUS-BYJUS@ICICI", "byjus", -15000.0, "education"),
    ("UPI-UNACADEMY-UNACADEMY@HDFC", "unacademy", -4200.0, "education"),
    ("SCHOOL FEE APRIL TERM", "school", -18000.0, "education"),
    ("COLLEGE TUITION SEMESTER FEE", "university", -45000.0, "education"),
    ("EXAM FEE GATE 2025", "exam board", -1500.0, "education"),
    ("UPGRAD COURSE PAYMENT", "upgrad", -40000.0, "education"),
    ("VEDANTU SUBSCRIPTION APR", "vedantu", -4999.0, "education"),
    ("SIMPLILEARN COURSE FEE", "simplilearn", -12000.0, "education"),

    # transfer
    ("UPI-SELF TRANSFER-SELF@HDFC", "self", -10000.0, "transfer"),
    ("NEFT TO ICICI ACCOUNT", "self", -25000.0, "transfer"),
    ("IMPS PAYMENT SENT", "phonepe", -5000.0, "transfer"),
    ("RTGS TRANSFER TO SBI", "sbi", -100000.0, "transfer"),
    ("UPI TRANSFER SENT PHONEPE", "phonepe", -3000.0, "transfer"),
    ("FUND TRANSFER TO SAVINGS", "hdfc", -20000.0, "transfer"),
    ("MONEY TRANSFER WISE", "wise", -8000.0, "transfer"),
    ("VENMO SPLIT BILL", "venmo", -32.0, "transfer"),
    ("ZELLE PAYMENT FRIEND", "zelle", -80.0, "transfer"),

    # housing
    ("RENT PAYMENT APRIL KRISHNA PROPERTY", "krishna property", -20000.0, "housing"),
    ("HOUSE RENT UPI OWNER", "landlord", -22000.0, "housing"),
    ("APARTMENT MAINTENANCE SOCIETY", "society", -3000.0, "housing"),
    ("PROPERTY TAX BBMP", "bbmp", -6000.0, "housing"),
    ("MORTGAGE EMI HOME LOAN", "hdfc home loan", -32000.0, "housing"),
    ("SOCIETY CHARGES QUARTERLY", "apartment society", -4500.0, "housing"),
    ("FLAT RENT MARCH", "owner", -18000.0, "housing"),
    ("MAINTENANCE CHARGES FLAT", "society", -2800.0, "housing"),

    # cash
    ("ATM WITHDRAWAL HDFC BANK", "hdfc atm", -4000.0, "cash"),
    ("CASH WDL SBI ATM KORAMANGALA", "sbi atm", -5000.0, "cash"),
    ("ATM TRANSACTION ICICI", "icici atm", -3000.0, "cash"),
    ("CASH WITHDRAWAL AXIS BANK ATM", "axis atm", -6000.0, "cash"),
    ("ATM WDL KOTAK MAHINDRA", "kotak atm", -2000.0, "cash"),

    # other – personal UPI payments (bulk of real data: local vendors, domestic help, etc.)
    ("UPI-DHINAKARAN K-PAYTMQR@PAYTM", "dhinakaran", -40.0, "other"),
    ("UPI-MS KARKUZHALI-GPAY@AXIS", "ms karkuzhali", -20.0, "other"),
    ("UPI-THILAGAVATHI IYYAPAN-EZE@CUB", "thilagavathi iyyapan", -65.0, "other"),
    ("UPI-MR R NANDHAKUMAR-SFFG@SBI", "mr r nandhakumar", -40.0, "other"),
    ("UPI-PERSONAL PAYMENT-NAME@UPI", "person name", -100.0, "other"),
    ("UPI-LOCAL VENDOR-VENDOR@PAYTM", "local vendor", -150.0, "other"),
    ("UPI-DOMESTIC HELP-HELP@SBI", "domestic help", -500.0, "other"),
    ("UPI-UNKNOWN MERCHANT-UPI@HDFC", "unknown", -200.0, "other"),
    ("UPI-STREET VENDOR-VENDOR@PAYTM", "street vendor", -50.0, "other"),
    ("PERSONAL PAYMENT UPI SENT", "person", -250.0, "other"),
    ("LOCAL SHOP PAYMENT UPI", "local shop", -80.0, "other"),
    ("MISCELLANEOUS PAYMENT SMALL", "misc", -30.0, "other"),
    ("SERVICE CHARGE ANNUAL", "bank", -150.0, "other"),
    ("BANK FEE DEBIT", "hdfc bank", -100.0, "other"),
    ("CONVENIENCE FEE GATEWAY", "payment gateway", -18.0, "other"),
    ("PROCESSING FEE DEDUCTION", "bank", -50.0, "other"),
    ("UNKNOWN DEBIT CHARGE", "unknown", -75.0, "other"),
    ("UPI PAYMENT SMALL VENDOR", "vendor", -35.0, "other"),
    ("PAYMENT TO INDIVIDUAL UPI", "individual", -300.0, "other"),
    ("DOMESTIC WORKER PAYMENT", "maid", -800.0, "other"),
    ("NEWSPAPER SUBSCRIPTION LOCAL", "vendor", -120.0, "other"),
    ("LAUNDRY SERVICE PAYMENT", "laundry", -200.0, "other"),
    ("TAILORING CHARGES PAYMENT", "tailor", -500.0, "other"),
    ("FRUIT VENDOR PAYMENT UPI", "vendor", -60.0, "other"),
    ("VEGETABLE MARKET PAYMENT", "vendor", -80.0, "other"),
]


# ---------------------------------------------------------------------------
# Feature engineering (must mirror categorization.py)
# ---------------------------------------------------------------------------

import re
from datetime import datetime

_NARRATION_PREFIXES = re.compile(
    r'^(pos|debit|credit|ach|wire|transfer|atm|neft|imps|upi|rtgs|nach|emi|int|chq|clg)\s*[/\-]?\s*',
    re.IGNORECASE,
)
_NOISE_PATTERNS = re.compile(r'\b(\d{6,}|[a-z0-9]{16,})\b')
_NON_ALPHA = re.compile(r'[^a-z\s]')


def _clean_text(text: str) -> str:
    text = text.lower().strip()
    text = _NARRATION_PREFIXES.sub('', text)
    text = _NOISE_PATTERNS.sub('', text)
    text = _NON_ALPHA.sub(' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _build_struct_array(amount: float) -> np.ndarray:
    """Return a 1-D structured feature vector (must match prediction in ml_service)."""
    return np.array([
        abs(amount),
        1 if amount < 0 else 0,   # is_debit
        1 if amount > 0 else 0,   # is_credit
        1 if abs(amount) > 10000 else 0,  # is_large
        1 if abs(amount) < 100 else 0,    # is_small
    ], dtype=float)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(output_path: str = "./models/categorizer.pkl") -> None:
    try:
        import scipy.sparse as sp
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report
    except ImportError as e:
        print(f"Missing dependency: {e}\nRun: pip install scikit-learn scipy")
        sys.exit(1)

    print(f"Training on {len(TRAINING_DATA)} labeled samples…")

    texts, struct_rows, labels = [], [], []
    for desc, merchant, amount, category in TRAINING_DATA:
        combined = _clean_text(f"{desc} {merchant}")
        texts.append(combined)
        struct_rows.append(_build_struct_array(amount))
        labels.append(category)

    # --- Encode labels ---
    le = LabelEncoder()
    y = le.fit_transform(labels)

    # --- TF-IDF features ---
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=3000,
        sublinear_tf=True,
    )
    X_text = tfidf.fit_transform(texts)

    # --- Stack structured features ---
    X_struct = sp.csr_matrix(np.array(struct_rows))
    X = sp.hstack([X_text, X_struct])

    # --- Train/test split ---
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- Train with balanced class weights ---
    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        max_depth=None,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # --- Evaluate ---
    y_pred = model.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    acc = (y_pred == y_test).mean()
    print(f"Test accuracy: {acc:.1%}")

    # --- Save ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model_data = {
        "model": model,
        "vectorizer": tfidf,
        "label_encoder": le,
        "use_structured_features": True,
        "struct_dim": X_struct.shape[1],
    }
    with open(output_path, "wb") as f:
        pickle.dump(model_data, f)

    print(f"\nModel saved -> {output_path}")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "./models/categorizer.pkl"
    train(output)

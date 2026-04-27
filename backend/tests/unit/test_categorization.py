"""Unit tests for the 3-tier transaction categorization service."""

import pytest
from datetime import date

from app.services.categorization import (
    normalize_merchant,
    clean_text,
    rule_engine,
    classify_transaction,
    batch_classify,
    detect_recurring,
    _keyword_scorer,
)


# ---------------------------------------------------------------------------
# normalize_merchant
# ---------------------------------------------------------------------------

class TestNormalizeMerchant:
    def test_known_variant_normalized(self):
        assert normalize_merchant("amzn mktp") == "amazon"

    def test_food_delivery_normalized(self):
        assert normalize_merchant("swiggy instamart") == "swiggy"
        assert normalize_merchant("zomato order") == "zomato"

    def test_ride_hailing_normalized(self):
        assert normalize_merchant("ola cabs") == "ola"

    def test_unknown_merchant_lowercased(self):
        assert normalize_merchant("SomeUnknownShop") == "someunknownshop"

    def test_empty_string_returned_as_is(self):
        assert normalize_merchant("") == ""

    def test_case_insensitive(self):
        assert normalize_merchant("AMAZON PAY") == "amazon"


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_strips_narration_prefix(self):
        result = clean_text("UPI/Swiggy Order 123456789")
        assert "upi" not in result
        assert "swiggy" in result

    def test_removes_long_digit_strings(self):
        result = clean_text("swiggy 998877665544")
        assert "998877665544" not in result
        assert "swiggy" in result

    def test_lowercases(self):
        result = clean_text("NETFLIX SUBSCRIPTION")
        assert result == result.lower()

    def test_collapses_whitespace(self):
        result = clean_text("zomato   order")
        assert "  " not in result

    def test_empty_string(self):
        assert clean_text("") == ""


# ---------------------------------------------------------------------------
# rule_engine
# ---------------------------------------------------------------------------

class TestRuleEngine:
    def test_food_delivery_match(self):
        result = rule_engine("zomato order")
        assert result is not None
        assert result[0] == "food"
        assert result[1] == 0.95

    def test_salary_income(self):
        result = rule_engine("salary credit from employer")
        assert result is not None
        assert result[0] == "income"

    def test_atm_cash(self):
        result = rule_engine("atm cash withdrawal")
        assert result is not None
        assert result[0] == "cash"

    def test_transport_uber(self):
        result = rule_engine("uber ride")
        assert result is not None
        assert result[0] == "transport"

    def test_utilities_electricity(self):
        result = rule_engine("bescom electricity bill")
        assert result is not None
        assert result[0] == "utilities"

    def test_entertainment_netflix(self):
        result = rule_engine("netflix subscription")
        assert result is not None
        assert result[0] == "entertainment"

    def test_healthcare_pharmacy(self):
        result = rule_engine("apollo pharmacy purchase")
        assert result is not None
        assert result[0] == "healthcare"

    def test_shopping_amazon(self):
        result = rule_engine("amazon order")
        assert result is not None
        assert result[0] == "shopping"

    def test_investment_zerodha(self):
        result = rule_engine("zerodha broking trade")
        assert result is not None
        assert result[0] == "investment"

    def test_housing_rent(self):
        result = rule_engine("rent payment")
        assert result is not None
        assert result[0] == "housing"

    def test_no_match_returns_none(self):
        result = rule_engine("xyzzy unknown transaction 123")
        assert result is None

    def test_returns_high_confidence(self):
        result = rule_engine("swiggy delivery")
        assert result[1] >= 0.90

    def test_refund_goes_to_income(self):
        result = rule_engine("refund from merchant")
        assert result is not None
        assert result[0] == "income"

    def test_transfer_neft(self):
        result = rule_engine("neft to john doe")
        assert result is not None
        assert result[0] == "transfer"


# ---------------------------------------------------------------------------
# classify_transaction — hybrid pipeline
# ---------------------------------------------------------------------------

class TestClassifyTransaction:
    def test_rule_wins_for_known_merchant(self):
        result = classify_transaction(description="netflix subscription", amount=499.0)
        assert result["category"] == "entertainment"
        assert result["method"] == "rule"
        assert result["confidence"] == 0.95

    def test_keyword_fallback_for_unknown(self):
        # A description with no rule match should fall through to keyword scorer
        result = classify_transaction(description="grocery store nearby")
        assert result["category"] in {"food", "shopping"}
        assert result["method"] in {"rule", "keyword", "ml"}

    def test_returns_required_keys(self):
        result = classify_transaction(description="swiggy order", amount=350.0)
        assert "category" in result
        assert "confidence" in result
        assert "method" in result

    def test_confidence_is_float_in_range(self):
        result = classify_transaction(description="airtel broadband bill")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_merchant_assists_classification(self):
        result = classify_transaction(description="payment", merchant="zomato order")
        assert result["category"] == "food"

    def test_empty_description_does_not_crash(self):
        result = classify_transaction(description="")
        assert "category" in result

    def test_txn_date_accepted(self):
        result = classify_transaction(
            description="petrol pump",
            amount=2000.0,
            txn_date=date(2024, 3, 15),
        )
        assert result["category"] == "transport"


# ---------------------------------------------------------------------------
# _keyword_scorer — fallback scorer
# ---------------------------------------------------------------------------

class TestKeywordScorer:
    def test_matches_food_keywords(self):
        cat, conf = _keyword_scorer("restaurant dinner")
        assert cat == "food"
        assert conf > 0.0

    def test_matches_transport_keywords(self):
        cat, conf = _keyword_scorer("uber ride payment")
        assert cat == "transport"

    def test_unknown_with_positive_amount_returns_income(self):
        cat, conf = _keyword_scorer("xyzzy123 random", amount=500.0)
        assert cat == "income"
        assert conf == 0.4

    def test_unknown_zero_amount_returns_other(self):
        cat, conf = _keyword_scorer("xyzzy123 random", amount=0.0)
        assert cat == "other"
        assert conf == 0.2


# ---------------------------------------------------------------------------
# detect_recurring
# ---------------------------------------------------------------------------

class TestDetectRecurring:
    def test_recurring_subscription_flagged(self):
        transactions = [
            {"date": "2024-01", "merchant": "netflix", "amount": 499.0},
            {"date": "2024-02", "merchant": "netflix", "amount": 499.0},
            {"date": "2024-03", "merchant": "netflix", "amount": 499.0},
        ]
        result = detect_recurring(transactions)
        assert all(t["is_recurring"] for t in result)

    def test_single_occurrence_not_recurring(self):
        transactions = [
            {"date": "2024-01", "merchant": "dentist", "amount": 2000.0},
        ]
        result = detect_recurring(transactions)
        assert result[0]["is_recurring"] is False

    def test_same_merchant_different_amounts_not_recurring(self):
        # Amounts vary by more than 5% tolerance
        transactions = [
            {"date": "2024-01", "merchant": "amazon", "amount": 500.0},
            {"date": "2024-02", "merchant": "amazon", "amount": 5000.0},
        ]
        result = detect_recurring(transactions)
        assert not any(t["is_recurring"] for t in result)

    def test_empty_list(self):
        assert detect_recurring([]) == []

    def test_preserves_original_fields(self):
        transactions = [
            {"date": "2024-01", "merchant": "spotify", "amount": 119.0, "extra": "data"},
        ]
        result = detect_recurring(transactions)
        assert result[0]["extra"] == "data"


# ---------------------------------------------------------------------------
# batch_classify
# ---------------------------------------------------------------------------

class TestBatchClassify:
    def test_returns_same_count(self):
        txns = [
            {"description": "swiggy order", "merchant": "swiggy", "amount": 350.0},
            {"description": "netflix subscription", "amount": 499.0},
        ]
        results = batch_classify(txns)
        assert len(results) == len(txns)

    def test_each_result_has_category(self):
        txns = [{"description": "uber ride", "amount": 200.0}]
        results = batch_classify(txns)
        assert "category" in results[0]

    def test_recurring_flag_added(self):
        txns = [
            {"description": "jio recharge", "merchant": "jio", "amount": 299.0, "date": "2024-01"},
            {"description": "jio recharge", "merchant": "jio", "amount": 299.0, "date": "2024-02"},
        ]
        results = batch_classify(txns)
        assert "is_recurring" in results[0]

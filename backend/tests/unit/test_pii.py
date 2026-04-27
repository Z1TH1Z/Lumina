"""Unit tests for PII detection and masking service."""

import pytest

from app.services.pii import detect_pii, mask_pii, sanitize_for_llm


# ---------------------------------------------------------------------------
# detect_pii
# ---------------------------------------------------------------------------

class TestDetectPii:
    def test_detects_ssn(self):
        findings = detect_pii("SSN: 123-45-6789")
        types = [f["type"] for f in findings]
        assert "ssn" in types

    def test_detects_credit_card(self):
        findings = detect_pii("Card: 4111 1111 1111 1111")
        types = [f["type"] for f in findings]
        assert "credit_card" in types

    def test_detects_email(self):
        findings = detect_pii("Contact: user@example.com")
        types = [f["type"] for f in findings]
        assert "email" in types

    def test_detects_phone_us(self):
        findings = detect_pii("Call me at 555-867-5309")
        types = [f["type"] for f in findings]
        assert "phone" in types

    def test_detects_account_number(self):
        findings = detect_pii("Account: 987654321")
        types = [f["type"] for f in findings]
        assert "account_number" in types

    def test_detects_routing_number(self):
        findings = detect_pii("Routing: 021000021")
        types = [f["type"] for f in findings]
        assert "routing_number" in types

    def test_no_pii_returns_empty_list(self):
        findings = detect_pii("This is a normal transaction note")
        assert findings == []

    def test_multiple_pii_types_in_one_text(self):
        text = "Email: test@bank.com, SSN: 000-11-2222"
        findings = detect_pii(text)
        types = [f["type"] for f in findings]
        assert "email" in types
        assert "ssn" in types

    def test_finding_has_required_keys(self):
        findings = detect_pii("user@test.com")
        assert len(findings) > 0
        keys = findings[0].keys()
        for key in ("type", "label", "start", "end", "text"):
            assert key in keys

    def test_finding_positions_are_correct(self):
        text = "Email: user@example.com"
        findings = detect_pii(text)
        email_finding = next(f for f in findings if f["type"] == "email")
        # The matched text should equal the slice at reported positions
        assert text[email_finding["start"]:email_finding["end"]] == email_finding["text"]


# ---------------------------------------------------------------------------
# mask_pii — redact method
# ---------------------------------------------------------------------------

class TestMaskPiiRedact:
    def test_ssn_is_redacted(self):
        result = mask_pii("SSN 123-45-6789 on file", method="redact")
        assert "123-45-6789" not in result["text"]
        assert "[REDACTED]" in result["text"]

    def test_pii_detected_flag_true(self):
        result = mask_pii("Email: john@example.com", method="redact")
        assert result["pii_detected"] is True

    def test_no_pii_flag_false(self):
        result = mask_pii("Normal transaction note", method="redact")
        assert result["pii_detected"] is False
        assert result["text"] == "Normal transaction note"

    def test_pii_count_correct(self):
        text = "SSN: 111-22-3333 and card 4111-1111-1111-1111"
        result = mask_pii(text, method="redact")
        assert result["pii_count"] == 2

    def test_findings_list_returned(self):
        result = mask_pii("user@test.com", method="redact")
        assert isinstance(result["findings"], list)
        assert len(result["findings"]) > 0

    def test_multiple_occurrences_all_redacted(self):
        text = "From: a@test.com To: b@test.com"
        result = mask_pii(text, method="redact")
        assert "a@test.com" not in result["text"]
        assert "b@test.com" not in result["text"]


# ---------------------------------------------------------------------------
# mask_pii — hash method
# ---------------------------------------------------------------------------

class TestMaskPiiHash:
    def test_ssn_replaced_with_hash_token(self):
        result = mask_pii("SSN: 123-45-6789", method="hash")
        assert "123-45-6789" not in result["text"]
        assert "[HASH:" in result["text"]

    def test_hash_length_is_12(self):
        result = mask_pii("user@test.com", method="hash")
        import re
        hashes = re.findall(r'\[HASH:([a-f0-9]+)\]', result["text"])
        assert all(len(h) == 12 for h in hashes)

    def test_same_input_produces_same_hash(self):
        text = "user@test.com"
        result1 = mask_pii(text, method="hash")
        result2 = mask_pii(text, method="hash")
        assert result1["text"] == result2["text"]


# ---------------------------------------------------------------------------
# mask_pii — token method
# ---------------------------------------------------------------------------

class TestMaskPiiToken:
    def test_ssn_gets_type_token(self):
        result = mask_pii("SSN: 000-11-2222", method="token")
        assert "[SSN_1]" in result["text"]

    def test_multiple_same_type_increments_counter(self):
        text = "Email: a@test.com and b@test.com"
        result = mask_pii(text, method="token")
        assert "[EMAIL_1]" in result["text"]
        assert "[EMAIL_2]" in result["text"]

    def test_token_preserves_non_pii_text(self):
        result = mask_pii("Hello user@example.com how are you", method="token")
        assert "Hello" in result["text"]
        assert "how are you" in result["text"]


# ---------------------------------------------------------------------------
# sanitize_for_llm
# ---------------------------------------------------------------------------

class TestSanitizeForLlm:
    def test_returns_string(self):
        result = sanitize_for_llm("Normal text")
        assert isinstance(result, str)

    def test_pii_not_in_sanitized_output(self):
        text = "Account: 123456789 Email: admin@bank.com"
        result = sanitize_for_llm(text)
        assert "123456789" not in result
        assert "admin@bank.com" not in result

    def test_clean_text_unchanged(self):
        text = "Swiggy food order total is 450"
        result = sanitize_for_llm(text)
        assert result == text

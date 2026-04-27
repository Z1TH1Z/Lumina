"""Unit tests for financial tools service."""

import pytest

from app.services.tools import (
    compound_interest,
    loan_amortization,
    tax_estimate,
    savings_goal,
    execute_tool,
)


# ---------------------------------------------------------------------------
# compound_interest
# ---------------------------------------------------------------------------

class TestCompoundInterest:
    def test_basic_calculation(self):
        result = compound_interest(principal=1000, annual_rate=10, years=1, compounds_per_year=1)
        assert result["final_amount"] == pytest.approx(1100.0, rel=1e-3)
        assert result["interest_earned"] == pytest.approx(100.0, rel=1e-3)

    def test_monthly_compounding(self):
        result = compound_interest(principal=1000, annual_rate=12, years=1, compounds_per_year=12)
        # Monthly compounding should yield slightly more than simple annual
        assert result["final_amount"] > 1120.0

    def test_zero_rate(self):
        result = compound_interest(principal=5000, annual_rate=0, years=5)
        assert result["final_amount"] == pytest.approx(5000.0, rel=1e-3)
        assert result["interest_earned"] == pytest.approx(0.0, abs=1e-2)

    def test_returns_required_keys(self):
        result = compound_interest(1000, 5, 2)
        for key in ("principal", "final_amount", "interest_earned", "annual_rate", "years"):
            assert key in result

    def test_principal_preserved(self):
        result = compound_interest(principal=2500, annual_rate=8, years=3)
        assert result["principal"] == 2500.0

    def test_result_rounded_to_two_decimals(self):
        result = compound_interest(1000, 7, 10)
        # Check no more than 2 decimal places
        assert result["final_amount"] == round(result["final_amount"], 2)


# ---------------------------------------------------------------------------
# loan_amortization
# ---------------------------------------------------------------------------

class TestLoanAmortization:
    def test_basic_loan(self):
        result = loan_amortization(principal=100000, annual_rate=10, years=10)
        assert result["monthly_payment"] > 0
        assert result["total_paid"] > 100000
        assert result["total_interest"] > 0

    def test_zero_rate_loan(self):
        result = loan_amortization(principal=12000, annual_rate=0, years=1, payments_per_year=12)
        assert result["monthly_payment"] == pytest.approx(1000.0, rel=1e-3)

    def test_total_paid_equals_payment_times_periods(self):
        result = loan_amortization(principal=50000, annual_rate=8, years=5)
        expected = result["monthly_payment"] * result["total_payments"]
        assert result["total_paid"] == pytest.approx(expected, rel=1e-2)

    def test_schedule_summary_not_empty(self):
        result = loan_amortization(principal=100000, annual_rate=5, years=10)
        assert len(result["schedule_summary"]) > 0

    def test_schedule_payment_fields(self):
        result = loan_amortization(principal=100000, annual_rate=5, years=10)
        entry = result["schedule_summary"][0]
        for key in ("payment_number", "payment", "principal", "interest", "balance"):
            assert key in entry

    def test_balance_decreases(self):
        result = loan_amortization(principal=100000, annual_rate=6, years=5)
        schedule = result["schedule_summary"]
        # First payment balance should be less than principal
        assert schedule[0]["balance"] < 100000

    def test_returns_total_payments(self):
        result = loan_amortization(principal=50000, annual_rate=5, years=3)
        assert result["total_payments"] == 36


# ---------------------------------------------------------------------------
# tax_estimate
# ---------------------------------------------------------------------------

class TestTaxEstimate:
    def test_single_filer_basic(self):
        result = tax_estimate(gross_income=50000, filing_status="single")
        assert result["estimated_tax"] > 0
        assert result["effective_rate"] > 0

    def test_married_filer(self):
        result = tax_estimate(gross_income=100000, filing_status="married")
        assert result["estimated_tax"] > 0

    def test_deductions_reduce_tax(self):
        no_deduction = tax_estimate(gross_income=80000, deductions=0, filing_status="single")
        with_deduction = tax_estimate(gross_income=80000, deductions=10000, filing_status="single")
        assert with_deduction["estimated_tax"] < no_deduction["estimated_tax"]

    def test_after_tax_income_is_gross_minus_tax(self):
        result = tax_estimate(gross_income=60000, filing_status="single")
        expected = result["gross_income"] - result["estimated_tax"]
        assert result["after_tax_income"] == pytest.approx(expected, rel=1e-3)

    def test_zero_income_zero_tax(self):
        result = tax_estimate(gross_income=0)
        assert result["estimated_tax"] == 0.0
        assert result["effective_rate"] == 0.0

    def test_taxable_income_is_gross_minus_deductions(self):
        result = tax_estimate(gross_income=100000, deductions=15000)
        assert result["taxable_income"] == pytest.approx(85000.0, rel=1e-3)

    def test_unknown_filing_status_defaults_to_single(self):
        single = tax_estimate(gross_income=70000, filing_status="single")
        unknown = tax_estimate(gross_income=70000, filing_status="other")
        assert single["estimated_tax"] == unknown["estimated_tax"]

    def test_returns_required_keys(self):
        result = tax_estimate(50000)
        for key in ("gross_income", "taxable_income", "estimated_tax", "effective_rate", "after_tax_income"):
            assert key in result


# ---------------------------------------------------------------------------
# savings_goal
# ---------------------------------------------------------------------------

class TestSavingsGoal:
    def test_basic_goal_reached(self):
        result = savings_goal(target_amount=12000, monthly_contribution=1000, annual_return=0)
        assert result["months_needed"] == pytest.approx(12, abs=1)

    def test_no_contribution_returns_none_months(self):
        result = savings_goal(target_amount=10000, monthly_contribution=0)
        assert result["months_needed"] is None
        assert "message" in result

    def test_already_at_target(self):
        result = savings_goal(target_amount=5000, current_savings=5000, monthly_contribution=100)
        assert result["months_needed"] == pytest.approx(0, abs=1)

    def test_returns_required_keys(self):
        result = savings_goal(target_amount=10000, monthly_contribution=500)
        for key in ("target", "months_needed", "years_needed", "total_contributed"):
            assert key in result

    def test_years_equals_months_divided_by_12(self):
        result = savings_goal(target_amount=24000, monthly_contribution=1000, annual_return=0)
        if result["months_needed"] is not None:
            assert result["years_needed"] == pytest.approx(result["months_needed"] / 12, rel=1e-2)

    def test_higher_return_reaches_goal_faster(self):
        low_return = savings_goal(target_amount=50000, monthly_contribution=500, annual_return=1.0)
        high_return = savings_goal(target_amount=50000, monthly_contribution=500, annual_return=10.0)
        assert high_return["months_needed"] <= low_return["months_needed"]


# ---------------------------------------------------------------------------
# execute_tool — dispatcher
# ---------------------------------------------------------------------------

class TestExecuteTool:
    def test_compound_interest_tool(self):
        result = execute_tool("compound_interest", {"principal": 1000, "annual_rate": 10, "years": 1})
        assert "result" in result
        assert result["tool"] == "compound_interest"

    def test_unknown_tool_returns_error(self):
        result = execute_tool("nonexistent_tool", {})
        assert "error" in result
        assert "available_tools" in result

    def test_bad_parameters_returns_error(self):
        result = execute_tool("compound_interest", {"principal": "not_a_number"})
        assert "error" in result

    def test_all_registered_tools_callable(self):
        calls = [
            ("compound_interest", {"principal": 1000, "annual_rate": 5, "years": 2}),
            ("loan_amortization", {"principal": 50000, "annual_rate": 6, "years": 5}),
            ("tax_estimate", {"gross_income": 60000}),
            ("savings_goal", {"target_amount": 10000, "monthly_contribution": 500}),
        ]
        for tool_name, params in calls:
            result = execute_tool(tool_name, params)
            assert "result" in result, f"{tool_name} should return a result"

"""Deterministic financial tool-calling service."""

import math
from typing import Optional
from app.services.sandbox import execute_sandboxed, SandboxError


def compound_interest(
    principal: float,
    annual_rate: float,
    years: float,
    compounds_per_year: int = 12,
) -> dict:
    """Calculate compound interest."""
    rate = annual_rate / 100
    amount = principal * (1 + rate / compounds_per_year) ** (compounds_per_year * years)
    interest = amount - principal
    return {
        "principal": round(principal, 2),
        "final_amount": round(amount, 2),
        "interest_earned": round(interest, 2),
        "annual_rate": annual_rate,
        "years": years,
        "compounds_per_year": compounds_per_year,
    }


def loan_amortization(
    principal: float,
    annual_rate: float,
    years: int,
    payments_per_year: int = 12,
) -> dict:
    """Generate a loan amortization schedule."""
    rate = annual_rate / 100 / payments_per_year
    total_payments = years * payments_per_year

    if rate == 0:
        monthly_payment = principal / total_payments
    else:
        monthly_payment = principal * (rate * (1 + rate) ** total_payments) / ((1 + rate) ** total_payments - 1)

    schedule = []
    balance = principal
    total_interest = 0

    for i in range(1, total_payments + 1):
        interest_payment = balance * rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        total_interest += interest_payment

        if i <= 12 or i > total_payments - 3:  # Show first year and last 3 payments
            schedule.append({
                "payment_number": i,
                "payment": round(monthly_payment, 2),
                "principal": round(principal_payment, 2),
                "interest": round(interest_payment, 2),
                "balance": round(max(balance, 0), 2),
            })

    return {
        "monthly_payment": round(monthly_payment, 2),
        "total_paid": round(monthly_payment * total_payments, 2),
        "total_interest": round(total_interest, 2),
        "schedule_summary": schedule,
        "total_payments": total_payments,
    }


def tax_estimate(
    gross_income: float,
    deductions: float = 0,
    filing_status: str = "single",
) -> dict:
    """Estimate US federal income tax (simplified 2024 brackets)."""
    # 2024 US Federal tax brackets (simplified)
    brackets = {
        "single": [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (float('inf'), 0.37),
        ],
        "married": [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float('inf'), 0.37),
        ],
    }

    status_brackets = brackets.get(filing_status, brackets["single"])
    taxable_income = max(gross_income - deductions, 0)

    tax = 0
    prev_limit = 0
    for limit, rate in status_brackets:
        if taxable_income <= prev_limit:
            break
        taxable_in_bracket = min(taxable_income, limit) - prev_limit
        tax += taxable_in_bracket * rate
        prev_limit = limit

    effective_rate = (tax / gross_income * 100) if gross_income > 0 else 0

    return {
        "gross_income": round(gross_income, 2),
        "deductions": round(deductions, 2),
        "taxable_income": round(taxable_income, 2),
        "estimated_tax": round(tax, 2),
        "effective_rate": round(effective_rate, 2),
        "filing_status": filing_status,
        "after_tax_income": round(gross_income - tax, 2),
    }


def savings_goal(
    target_amount: float,
    current_savings: float = 0,
    monthly_contribution: float = 0,
    annual_return: float = 7.0,
) -> dict:
    """Calculate time to reach a savings goal."""
    monthly_rate = annual_return / 100 / 12
    remaining = target_amount - current_savings

    if monthly_contribution <= 0:
        return {
            "target": target_amount,
            "current": current_savings,
            "remaining": round(remaining, 2),
            "months_needed": None,
            "message": "Monthly contribution required to calculate timeline.",
        }

    if monthly_rate == 0:
        months = remaining / monthly_contribution
    else:
        # Solve: target = current*(1+r)^n + contribution*((1+r)^n - 1)/r
        # Using iterative approach
        months = 0
        balance = current_savings
        while balance < target_amount and months < 1200:
            balance = balance * (1 + monthly_rate) + monthly_contribution
            months += 1

    years = months / 12

    return {
        "target": round(target_amount, 2),
        "current_savings": round(current_savings, 2),
        "monthly_contribution": round(monthly_contribution, 2),
        "annual_return": annual_return,
        "months_needed": months,
        "years_needed": round(years, 1),
        "total_contributed": round(monthly_contribution * months, 2),
        "total_growth": round(target_amount - current_savings - monthly_contribution * months, 2),
    }


# Tool registry for LLM tool-calling
AVAILABLE_TOOLS = {
    "compound_interest": {
        "function": compound_interest,
        "description": "Calculate compound interest on an investment",
        "parameters": {
            "principal": "Initial investment amount",
            "annual_rate": "Annual interest rate (percentage)",
            "years": "Time period in years",
            "compounds_per_year": "Number of times interest compounds per year (default: 12)",
        },
    },
    "loan_amortization": {
        "function": loan_amortization,
        "description": "Generate a loan amortization schedule",
        "parameters": {
            "principal": "Loan amount",
            "annual_rate": "Annual interest rate (percentage)",
            "years": "Loan term in years",
        },
    },
    "tax_estimate": {
        "function": tax_estimate,
        "description": "Estimate US federal income tax",
        "parameters": {
            "gross_income": "Annual gross income",
            "deductions": "Total deductions (default: 0)",
            "filing_status": "Filing status: 'single' or 'married'",
        },
    },
    "savings_goal": {
        "function": savings_goal,
        "description": "Calculate time to reach a savings goal",
        "parameters": {
            "target_amount": "Target savings amount",
            "current_savings": "Current savings (default: 0)",
            "monthly_contribution": "Monthly contribution amount",
            "annual_return": "Expected annual return percentage (default: 7%)",
        },
    },
}


def execute_tool(tool_name: str, parameters: dict) -> dict:
    """Execute a financial tool by name."""
    tool = AVAILABLE_TOOLS.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}", "available_tools": list(AVAILABLE_TOOLS.keys())}

    try:
        result = tool["function"](**parameters)
        return {"tool": tool_name, "result": result}
    except Exception as e:
        return {"tool": tool_name, "error": str(e)}


def execute_custom_calculation(code: str, variables: dict = None) -> dict:
    """Execute custom sandboxed calculation."""
    try:
        result = execute_sandboxed(code, variables)
        return {"success": True, "result": result}
    except SandboxError as e:
        return {"success": False, "error": str(e)}

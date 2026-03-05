"""Unit tests for anomaly detection Celery worker."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.core.constants import ANOMALY_ZSCORE_THRESHOLD


def test_detect_transaction_anomalies_z_score_threshold():
    """Test that Z-score threshold constant is set correctly."""
    assert ANOMALY_ZSCORE_THRESHOLD == 2.5


def test_anomaly_schema_creation():
    """Test that Anomaly schema can be instantiated."""
    from app.schemas.transaction import Anomaly

    anomaly = Anomaly(
        transaction_id=1,
        z_score=Decimal("3.5"),
        explanation="This food transaction of $500.00 is 3.5 standard deviations above your average",
        detected_at=datetime.utcnow()
    )
    assert anomaly.transaction_id == 1
    assert anomaly.z_score == Decimal("3.5")
    assert "3.5 standard deviations" in anomaly.explanation


def test_forecast_schema_creation():
    """Test that Forecast schema can be instantiated."""
    from app.schemas.transaction import Forecast

    forecast = Forecast(
        period_months=3,
        predicted_amount=Decimal("1500.00"),
        confidence_interval_lower=Decimal("1200.00"),
        confidence_interval_upper=Decimal("1800.00"),
        category="food"
    )
    assert forecast.period_months == 3
    assert forecast.predicted_amount == Decimal("1500.00")
    assert forecast.category == "food"


def test_forecast_schema_no_category():
    """Test that Forecast schema works without a category."""
    from app.schemas.transaction import Forecast

    forecast = Forecast(
        period_months=6,
        predicted_amount=Decimal("3000.00"),
        confidence_interval_lower=Decimal("2500.00"),
        confidence_interval_upper=Decimal("3500.00"),
    )
    assert forecast.category is None

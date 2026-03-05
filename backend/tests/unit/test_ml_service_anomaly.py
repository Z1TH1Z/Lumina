"""Unit tests for MLService anomaly detection."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.ml_service import MLService
from app.models.transaction import Transaction
from app.core.constants import ANOMALY_ZSCORE_THRESHOLD


@pytest.fixture
def ml_service():
    """Create MLService instance."""
    return MLService()


@pytest.fixture
def sample_transactions():
    """Create sample transactions for testing using MagicMock."""
    transactions = []

    # Create normal food transactions
    for amount in [50.0, 55.0, 52.0, 48.0, 53.0]:
        tx = MagicMock(spec=Transaction)
        tx.id = 1
        tx.user_id = 1
        tx.category = "food"
        tx.amount = Decimal(str(amount))
        tx.date = date(2024, 1, 1)
        transactions.append(tx)

    # Create an anomalous food transaction (much higher than average)
    tx_anomaly = MagicMock(spec=Transaction)
    tx_anomaly.id = 6
    tx_anomaly.user_id = 1
    tx_anomaly.category = "food"
    tx_anomaly.amount = Decimal("200.0")
    tx_anomaly.date = date(2024, 1, 15)
    transactions.append(tx_anomaly)

    return transactions


def test_detect_anomalies_returns_list(ml_service, sample_transactions):
    """Test detect_anomalies returns a list of anomalies."""
    user_id = "1"
    anomalies = ml_service.detect_anomalies(sample_transactions, user_id)
    assert isinstance(anomalies, list)


def test_detect_anomalies_finds_outlier(ml_service, sample_transactions):
    """Test detect_anomalies flags the high-value transaction."""
    user_id = "1"
    anomalies = ml_service.detect_anomalies(sample_transactions, user_id)

    # The $200 transaction should be flagged — it is far above the ~50 average
    assert len(anomalies) > 0

    anomaly_tx_ids = [a.transaction_id for a in anomalies]
    assert 6 in anomaly_tx_ids


def test_detect_anomalies_empty_list(ml_service):
    """Test detect_anomalies with empty transaction list."""
    anomalies = ml_service.detect_anomalies([], "1")
    assert anomalies == []


def test_detect_anomalies_insufficient_data(ml_service):
    """Test detect_anomalies with less than 3 transactions (not enough for statistics)."""
    tx1 = MagicMock(spec=Transaction)
    tx1.id = 1
    tx1.category = "food"
    tx1.amount = Decimal("50.0")

    tx2 = MagicMock(spec=Transaction)
    tx2.id = 2
    tx2.category = "food"
    tx2.amount = Decimal("55.0")

    anomalies = ml_service.detect_anomalies([tx1, tx2], "1")
    # With < 3 transactions per category, no anomalies should be detected
    assert anomalies == []


def test_detect_anomalies_uniform_amounts(ml_service):
    """Test detect_anomalies when all amounts are identical (std=0)."""
    transactions = []
    for i in range(5):
        tx = MagicMock(spec=Transaction)
        tx.id = i
        tx.category = "utilities"
        tx.amount = Decimal("100.0")
        tx.date = date(2024, 1, 1)
        transactions.append(tx)

    anomalies = ml_service.detect_anomalies(transactions, "1")
    # All amounts are the same, std=0, so no anomalies
    assert anomalies == []


def test_detect_anomalies_explanation_content(ml_service, sample_transactions):
    """Test detect_anomalies generates explanations with expected content."""
    anomalies = ml_service.detect_anomalies(sample_transactions, "1")

    for anomaly in anomalies:
        assert anomaly.explanation
        assert "standard deviations" in anomaly.explanation
        assert "food" in anomaly.explanation
        assert anomaly.z_score is not None


def test_detect_anomalies_multiple_categories(ml_service):
    """Test detect_anomalies handles multiple categories independently."""
    transactions = []

    # Normal food transactions
    for i, amount in enumerate([50.0, 55.0, 52.0]):
        tx = MagicMock(spec=Transaction)
        tx.id = i
        tx.category = "food"
        tx.amount = Decimal(str(amount))
        tx.date = date(2024, 1, 1)
        transactions.append(tx)

    # Normal transport transactions
    for i, amount in enumerate([20.0, 22.0, 21.0], start=10):
        tx = MagicMock(spec=Transaction)
        tx.id = i
        tx.category = "transport"
        tx.amount = Decimal(str(amount))
        tx.date = date(2024, 1, 1)
        transactions.append(tx)

    # Add anomalous transport transaction
    tx_anomaly = MagicMock(spec=Transaction)
    tx_anomaly.id = 99
    tx_anomaly.category = "transport"
    tx_anomaly.amount = Decimal("200.0")
    tx_anomaly.date = date(2024, 1, 15)
    transactions.append(tx_anomaly)

    anomalies = ml_service.detect_anomalies(transactions, "1")

    # The $200 transport transaction should be flagged
    anomaly_ids = [a.transaction_id for a in anomalies]
    assert 99 in anomaly_ids

    # The food transactions should NOT be flagged
    for i in range(3):
        assert i not in anomaly_ids


def test_anomaly_zscore_threshold_constant():
    """Test the Z-score threshold constant value."""
    assert ANOMALY_ZSCORE_THRESHOLD == 2.5

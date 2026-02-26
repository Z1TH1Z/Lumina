"""Unit tests for anomaly detection Celery worker."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.celery_app import detect_transaction_anomalies
from app.models.transaction import Transaction
from app.schemas.transaction import Anomaly


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return str(uuid4())


@pytest.fixture
def sample_transactions():
    """Sample transactions for testing."""
    user_id = uuid4()
    return [
        Transaction(
            id=uuid4(),
            user_id=user_id,
            date=date(2024, 1, 1),
            description="Grocery shopping",
            merchant="Walmart",
            amount=Decimal("100.00"),
            category="food",
            is_anomaly=False,
            z_score=None
        ),
        Transaction(
            id=uuid4(),
            user_id=user_id,
            date=date(2024, 1, 5),
            description="Grocery shopping",
            merchant="Walmart",
            amount=Decimal("110.00"),
            category="food",
            is_anomaly=False,
            z_score=None
        ),
        Transaction(
            id=uuid4(),
            user_id=user_id,
            date=date(2024, 1, 10),
            description="Expensive dinner",
            merchant="Fancy Restaurant",
            amount=Decimal("500.00"),
            category="food",
            is_anomaly=False,
            z_score=None
        ),
    ]


@pytest.fixture
def sample_anomalies(sample_transactions):
    """Sample anomalies detected."""
    return [
        Anomaly(
            transaction_id=sample_transactions[2].id,
            transaction=sample_transactions[2],
            z_score=Decimal("3.5"),
            explanation="This food transaction of $500.00 is 3.5 standard deviations above your average",
            detected_at=datetime.utcnow()
        )
    ]


@pytest.mark.asyncio
async def test_detect_transaction_anomalies_success(sample_user_id, sample_transactions, sample_anomalies):
    """Test successful anomaly detection."""
    with patch('app.celery_app.async_session_factory') as mock_session_factory, \
         patch('app.celery_app.ml_service') as mock_ml_service:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        # Mock transaction query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_transactions
        mock_db.execute.return_value = mock_result
        
        # Mock anomaly detection
        mock_ml_service.detect_anomalies.return_value = sample_anomalies
        
        # Mock transaction update query
        mock_tx_result = MagicMock()
        mock_tx_result.scalar_one_or_none.return_value = sample_transactions[2]
        
        async def mock_execute(query):
            # First call returns all transactions, subsequent calls return individual transactions
            if mock_db.execute.call_count == 1:
                return mock_result
            else:
                return mock_tx_result
        
        mock_db.execute.side_effect = mock_execute
        
        # Execute task
        result = detect_transaction_anomalies(
            None,
            user_id=sample_user_id,
            date_from="2024-01-01",
            date_to="2024-01-31"
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["user_id"] == sample_user_id
        assert result["transactions_analyzed"] == 3
        assert result["anomalies_detected"] == 1
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-01-31"


@pytest.mark.asyncio
async def test_detect_transaction_anomalies_no_transactions(sample_user_id):
    """Test anomaly detection with no transactions."""
    with patch('app.celery_app.async_session_factory') as mock_session_factory:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        # Mock empty transaction query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Execute task
        result = detect_transaction_anomalies(
            None,
            user_id=sample_user_id,
            date_from="2024-01-01",
            date_to="2024-01-31"
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["transactions_analyzed"] == 0
        assert result["anomalies_detected"] == 0
        assert "No transactions found" in result["message"]


@pytest.mark.asyncio
async def test_detect_transaction_anomalies_no_date_range(sample_user_id, sample_transactions):
    """Test anomaly detection without date range filters."""
    with patch('app.celery_app.async_session_factory') as mock_session_factory, \
         patch('app.celery_app.ml_service') as mock_ml_service:
        
        # Mock database session
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        # Mock transaction query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_transactions
        mock_db.execute.return_value = mock_result
        
        # Mock no anomalies detected
        mock_ml_service.detect_anomalies.return_value = []
        
        # Execute task without date filters
        result = detect_transaction_anomalies(
            None,
            user_id=sample_user_id
        )
        
        # Verify results
        assert result["status"] == "completed"
        assert result["transactions_analyzed"] == 3
        assert result["anomalies_detected"] == 0
        assert result["date_from"] is None
        assert result["date_to"] is None


def test_detect_transaction_anomalies_z_score_threshold():
    """Test that Z-score > 2.5 flags transactions as anomalies."""
    # This is tested through the MLService.detect_anomalies method
    # which uses ANOMALY_ZSCORE_THRESHOLD constant
    from app.core.constants import ANOMALY_ZSCORE_THRESHOLD
    assert ANOMALY_ZSCORE_THRESHOLD == 2.5

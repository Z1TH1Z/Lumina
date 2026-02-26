"""Unit tests for MLService anomaly detection."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.ml_service import MLService
from app.models.transaction import Transaction


@pytest.fixture
def ml_service():
    """Create MLService instance."""
    return MLService()


@pytest.fixture
def sample_transactions():
    """Create sample transactions for testing."""
    user_id = uuid4()
    transactions = []
    
    # Create normal food transactions
    for amount in [50.0, 55.0, 52.0, 48.0, 53.0]:
        tx = MagicMock(spec=Transaction)
        tx.id = uuid4()
        tx.user_id = user_id
        tx.category = "food"
        tx.amount = Decimal(str(amount))
        tx.date = date(2024, 1, 1)
        transactions.append(tx)
    
    # Create an anomalous food transaction
    tx_anomaly = MagicMock(spec=Transaction)
    tx_anomaly.id = uuid4()
    tx_anomaly.user_id = user_id
    tx_anomaly.category = "food"
    tx_anomaly.amount = Decimal("200.0")  # Much higher than average
    tx_anomaly.date = date(2024, 1, 15)
    transactions.append(tx_anomaly)
    
    return transactions


def test_compute_statistics(ml_service, sample_transactions):
    """Test compute_statistics calculates mean and std correctly."""
    statistics = ml_service.compute_statistics(sample_transactions)
    
    assert "food" in statistics
    assert "mean" in statistics["food"]
    assert "std" in statistics["food"]
    
    # Check that mean is reasonable (should be around 75-80 with the anomaly)
    assert 60 < statistics["food"]["mean"] < 90
    assert statistics["food"]["std"] > 0


def test_compute_statistics_empty_list(ml_service):
    """Test compute_statistics with empty transaction list."""
    statistics = ml_service.compute_statistics([])
    assert statistics == {}


def test_compute_statistics_insufficient_data(ml_service):
    """Test compute_statistics with less than 3 transactions per category."""
    tx1 = MagicMock(spec=Transaction)
    tx1.category = "food"
    tx1.amount = Decimal("50.0")
    
    tx2 = MagicMock(spec=Transaction)
    tx2.category = "food"
    tx2.amount = Decimal("55.0")
    
    statistics = ml_service.compute_statistics([tx1, tx2])
    
    # Should not include category with less than 3 transactions
    assert "food" not in statistics


def test_calculate_z_score(ml_service):
    """Test calculate_z_score calculates correctly."""
    tx = MagicMock(spec=Transaction)
    tx.category = "food"
    tx.amount = Decimal("100.0")
    
    statistics = {
        "food": {
            "mean": 50.0,
            "std": 10.0
        }
    }
    
    z_score = ml_service.calculate_z_score(tx, statistics)
    
    # Z-score should be (100 - 50) / 10 = 5.0
    assert z_score == 5.0


def test_calculate_z_score_zero_std(ml_service):
    """Test calculate_z_score with zero standard deviation."""
    tx = MagicMock(spec=Transaction)
    tx.category = "food"
    tx.amount = Decimal("50.0")
    
    statistics = {
        "food": {
            "mean": 50.0,
            "std": 0.0
        }
    }
    
    z_score = ml_service.calculate_z_score(tx, statistics)
    
    # Should return 0.0 when std is 0
    assert z_score == 0.0


def test_calculate_z_score_no_statistics(ml_service):
    """Test calculate_z_score when category not in statistics."""
    tx = MagicMock(spec=Transaction)
    tx.category = "food"
    tx.amount = Decimal("50.0")
    
    statistics = {}
    
    z_score = ml_service.calculate_z_score(tx, statistics)
    
    # Should return None when no statistics available
    assert z_score is None


@pytest.mark.asyncio
async def test_detect_anomalies_with_cache(ml_service, sample_transactions):
    """Test detect_anomalies uses Redis cache."""
    user_id = str(uuid4())
    
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # No cached data
    mock_redis.setex.return_value = True
    
    with patch('app.services.ml_service.get_redis_client', return_value=mock_redis):
        anomalies = await ml_service.detect_anomalies(sample_transactions, user_id)
    
    # Should have detected the anomalous transaction
    assert len(anomalies) > 0
    
    # Verify Redis was called
    mock_redis.get.assert_called_once()
    mock_redis.setex.assert_called_once()
    
    # Check that cache key includes user_id
    cache_key = mock_redis.get.call_args[0][0]
    assert user_id in cache_key


@pytest.mark.asyncio
async def test_detect_anomalies_uses_cached_statistics(ml_service, sample_transactions):
    """Test detect_anomalies uses cached statistics when available."""
    user_id = str(uuid4())
    
    # Mock cached statistics
    cached_stats = {
        "food": {
            "mean": 51.6,
            "std": 2.5
        }
    }
    
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(cached_stats)
    
    with patch('app.services.ml_service.get_redis_client', return_value=mock_redis):
        anomalies = await ml_service.detect_anomalies(sample_transactions, user_id)
    
    # Should have detected anomalies using cached stats
    assert len(anomalies) > 0
    
    # Verify Redis get was called but setex was not (using cached data)
    mock_redis.get.assert_called_once()
    mock_redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_detect_anomalies_empty_list(ml_service):
    """Test detect_anomalies with empty transaction list."""
    user_id = str(uuid4())
    
    anomalies = await ml_service.detect_anomalies([], user_id)
    
    assert anomalies == []


@pytest.mark.asyncio
async def test_detect_anomalies_explanation(ml_service, sample_transactions):
    """Test detect_anomalies generates proper explanations."""
    user_id = str(uuid4())
    
    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    
    with patch('app.services.ml_service.get_redis_client', return_value=mock_redis):
        anomalies = await ml_service.detect_anomalies(sample_transactions, user_id)
    
    # Check that anomalies have explanations
    for anomaly in anomalies:
        assert anomaly.explanation
        assert "standard deviations" in anomaly.explanation
        assert "food" in anomaly.explanation
        assert anomaly.z_score is not None


@pytest.mark.asyncio
async def test_detect_anomalies_redis_error_handling(ml_service, sample_transactions):
    """Test detect_anomalies handles Redis errors gracefully."""
    user_id = str(uuid4())
    
    # Mock Redis client that raises an error
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection error")
    
    with patch('app.services.ml_service.get_redis_client', return_value=mock_redis):
        # Should not raise exception, should compute statistics directly
        anomalies = await ml_service.detect_anomalies(sample_transactions, user_id)
    
    # Should still detect anomalies despite Redis error
    assert len(anomalies) > 0

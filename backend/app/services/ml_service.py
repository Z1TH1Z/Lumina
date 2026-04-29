"""ML service for transaction categorization, anomaly detection, and forecasting."""

import os
import pickle
import logging
import numpy as np
from typing import Tuple, List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from pathlib import Path

# app.core.constants has no heavy dependencies — always safe to import.
from app.core.constants import (
    CATEGORIZATION_CONFIDENCE_THRESHOLD,
    ANOMALY_ZSCORE_THRESHOLD,
    FORECAST_MIN_MONTHS,
)

# pydantic / SQLAlchemy / aiosqlite are NOT imported at the top level so that
# ml_service can be loaded from notebook kernels that only have sklearn/numpy.
# Heavy app imports are deferred inside the methods that need them.

logger = logging.getLogger(__name__)


def _resolve_model_path() -> Path:
    """
    Return the absolute path to categorizer.pkl.

    Priority:
      1. CATEGORIZER_MODEL_PATH already in os.environ (set by shell or app startup)
      2. CATEGORIZER_MODEL_PATH in backend/.env  (parsed without pydantic)
      3. Default: <backend_root>/models/categorizer.pkl
    """
    backend_root = Path(__file__).parent.parent.parent

    env_val = os.environ.get("CATEGORIZER_MODEL_PATH", "")
    if not env_val:
        # Lightweight .env parse — no pydantic needed
        env_file = backend_root / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("CATEGORIZER_MODEL_PATH="):
                    env_val = line.split("=", 1)[1].strip()
                    break

    if env_val:
        p = Path(env_val)
        return p if p.is_absolute() else backend_root / p

    return backend_root / "models" / "categorizer.pkl"


async def get_redis_client():
    """Get Redis client for caching."""
    from redis.asyncio import Redis
    from app.core.config import get_settings
    settings = get_settings()
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


class MLService:
    """Service for ML-based operations."""

    def __init__(self):
        self._categorizer_model = None
        self._model_path = _resolve_model_path()

    def load_categorization_model(self):
        """Load the transaction categorization model."""
        if self._categorizer_model is None:
            try:
                with open(self._model_path, 'rb') as f:
                    self._categorizer_model = pickle.load(f)
                logger.info("Loaded categorization model from %s", self._model_path)
            except FileNotFoundError:
                logger.warning("Categorization model not found at %s", self._model_path)
                logger.warning("Run: python -m app.ml.train_categorizer")
                self._categorizer_model = None
            except Exception as exc:
                logger.warning(
                    "Failed loading categorization model from %s (%s: %s)",
                    self._model_path,
                    type(exc).__name__,
                    exc,
                )
                self._categorizer_model = None
        
        return self._categorizer_model

    def predict_category(
        self,
        description: str,
        features: Optional[Dict] = None,
    ) -> Tuple[str, float]:
        """
        Predict transaction category using ML model.

        Args:
            description: Cleaned transaction text (description + merchant, pre-cleaned)
            features: Structured feature dict from categorization.extract_features()

        Returns:
            Tuple of (category, confidence_score)
        """
        model_data = self.load_categorization_model()

        if model_data is None:
            raise RuntimeError(
                f"Categorization model not found at {self._model_path}. "
                "Run: cd backend && python -m app.ml.train_categorizer"
            )

        vectorizer = model_data['vectorizer']
        model = model_data['model']
        label_encoder = model_data['label_encoder']
        use_struct = model_data.get("use_structured_features", False)

        # TF-IDF text features
        X = vectorizer.transform([description])

        # Stack structured features if the model was trained with them
        if use_struct and features:
            try:
                import scipy.sparse as sp
                struct_vec = np.array([[
                    features.get("amount_abs", 0),
                    features.get("is_debit", 0),
                    features.get("is_credit", 0),
                    features.get("is_large", 0),
                    features.get("is_small", 0),
                ]], dtype=float)
                X = sp.hstack([X, sp.csr_matrix(struct_vec)])
            except Exception:
                pass  # fall back to text-only if stacking fails

        y_pred = model.predict(X)
        y_proba = model.predict_proba(X)

        category = label_encoder.inverse_transform(y_pred)[0]
        confidence = float(np.max(y_proba))

        return category, confidence

    def detect_anomalies(
        self,
        transactions,
        user_id: str,
    ) -> list:
        """
        Detect anomalies in transactions using Z-score analysis.

        Args:
            transactions: List of transactions to analyze
            user_id: User ID

        Returns:
            List of detected anomalies
        """
        from app.schemas.transaction import Anomaly  # deferred to avoid aiosqlite at import

        if not transactions:
            return []

        anomalies = []

        # Group transactions by category
        category_groups = {}
        for tx in transactions:
            if tx.category not in category_groups:
                category_groups[tx.category] = []
            category_groups[tx.category].append(tx)

        # Calculate Z-scores per category
        for category, txs in category_groups.items():
            if len(txs) < 3:
                # Need at least 3 transactions for meaningful statistics
                continue

            amounts = [float(tx.amount) for tx in txs]
            mean = np.mean(amounts)
            std = np.std(amounts)

            if std == 0:
                # All amounts are the same, no anomalies
                continue

            for tx in txs:
                z_score = (float(tx.amount) - mean) / std
                
                if abs(z_score) > ANOMALY_ZSCORE_THRESHOLD:
                    # Generate explanation
                    if z_score > 0:
                        explanation = f"This {category} transaction of ${tx.amount} is {abs(z_score):.1f} standard deviations above your average of ${mean:.2f}"
                    else:
                        explanation = f"This {category} transaction of ${tx.amount} is {abs(z_score):.1f} standard deviations below your average of ${mean:.2f}"

                    anomalies.append(Anomaly(
                        transaction_id=tx.id,
                        transaction=tx,
                        z_score=Decimal(str(z_score)),
                        explanation=explanation,
                        detected_at=datetime.utcnow()
                    ))

        return anomalies

    def generate_forecast(
        self,
        transactions,
        periods: List[int],
    ) -> list:
        """
        Generate spending forecasts using simple exponential smoothing.

        Args:
            transactions: Historical transactions
            periods: List of forecast periods in months

        Returns:
            List of forecasts
        """
        if not transactions:
            return []

        # Check if we have enough data (at least 3 months)
        if len(transactions) < FORECAST_MIN_MONTHS * 10:  # Rough estimate
            raise ValueError(f"Insufficient data: need at least {FORECAST_MIN_MONTHS} months of transactions")

        # Group by month and calculate monthly spending
        monthly_spending = {}
        for tx in transactions:
            month_key = tx.date.strftime("%Y-%m")
            if month_key not in monthly_spending:
                monthly_spending[month_key] = 0
            monthly_spending[month_key] += float(tx.amount)

        # Sort by month
        sorted_months = sorted(monthly_spending.keys())
        amounts = [monthly_spending[m] for m in sorted_months]

        if len(amounts) < FORECAST_MIN_MONTHS:
            raise ValueError(f"Insufficient data: need at least {FORECAST_MIN_MONTHS} months")

        from app.schemas.transaction import Forecast  # deferred to avoid aiosqlite at import

        # Simple exponential smoothing
        alpha = 0.3  # Smoothing factor
        forecasts = []

        for period in periods:
            # Calculate forecast
            forecast_value = amounts[-1]  # Start with last value
            for _ in range(period):
                forecast_value = alpha * amounts[-1] + (1 - alpha) * forecast_value

            # Calculate confidence interval (simple approach)
            std = np.std(amounts)
            confidence_interval = 1.96 * std  # 95% confidence

            forecasts.append(Forecast(
                period_months=period,
                predicted_amount=Decimal(str(forecast_value)),
                confidence_interval_lower=Decimal(str(max(0, forecast_value - confidence_interval))),
                confidence_interval_upper=Decimal(str(forecast_value + confidence_interval)),
                category=None
            ))

        return forecasts

    async def retrain_categorizer(
        self,
        user_corrections: List[Tuple[str, str]]
    ):
        """
        Retrain categorizer with user corrections (placeholder).

        Args:
            user_corrections: List of (text, correct_category) tuples
        """
        # In a production system, this would:
        # 1. Collect user corrections
        # 2. Periodically retrain the model
        # 3. Evaluate on validation set
        # 4. Deploy new model if performance improves
        
        print(f"📝 Collected {len(user_corrections)} user corrections for future retraining")
        pass


# Global instance
ml_service = MLService()

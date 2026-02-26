"""Celery worker configuration for async task processing."""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_financial_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=300,
    task_time_limit=600,
)


@celery_app.task(name="extract_text_from_pdf", bind=True)
def extract_text_from_pdf(self, document_id: str):
    """
    Celery task: Extract text from PDF using OCR and parse transactions.

    Args:
        document_id: Document ID (UUID as string)

    Returns:
        Dict with extraction results
    """
    from uuid import UUID
    from app.utils.ocr import ocr_processor
    from app.utils.transaction_parser import transaction_parser
    from app.database import async_session_factory
    from app.services.document_service import DocumentService
    from app.models.transaction import Transaction
    from app.core.constants import (
        DOCUMENT_STATUS_PROCESSING,
        DOCUMENT_STATUS_COMPLETED,
        DOCUMENT_STATUS_FAILED,
        DOCUMENT_STATUS_MANUAL_REVIEW,
    )
    import asyncio

    async def process():
        async with async_session_factory() as db:
            doc_service = DocumentService(db)
            doc_id = UUID(document_id)

            # Update status to processing
            document = await doc_service.update_document_status(
                doc_id,
                DOCUMENT_STATUS_PROCESSING
            )

            if not document:
                return {"error": "Document not found"}

            try:
                # Extract text using OCR
                text, metadata = ocr_processor.extract_text(document.file_path)

                # Parse transactions from extracted text
                tables = metadata.get("tables", [])
                transactions, parse_success = transaction_parser.parse_transactions(text, tables)

                # Create transaction records
                created_transactions = []
                transaction_ids = []
                if transactions:
                    for tx_data in transactions:
                        transaction = Transaction(
                            user_id=document.user_id,
                            document_id=doc_id,
                            date=tx_data["date"],
                            description=tx_data["description"],
                            merchant=tx_data.get("merchant"),
                            amount=tx_data["amount"],
                            category="other",  # Will be categorized by ML model
                            metadata={"raw_text": tx_data.get("raw_text")}
                        )
                        db.add(transaction)
                        created_transactions.append(transaction)

                    await db.commit()
                    
                    # Get transaction IDs for categorization
                    for tx in created_transactions:
                        await db.refresh(tx)
                        transaction_ids.append(str(tx.id))

                    # Trigger categorization task
                    if transaction_ids:
                        from app.celery_app import categorize_transactions
                        categorize_transactions.delay(transaction_ids)

                # Update document status
                if parse_success:
                    status = DOCUMENT_STATUS_COMPLETED
                else:
                    # No transactions found - mark for manual review
                    status = DOCUMENT_STATUS_MANUAL_REVIEW

                metadata["transaction_count"] = len(transactions)
                await doc_service.update_document_status(
                    doc_id,
                    status,
                    raw_text=text,
                    metadata=metadata
                )

                return {
                    "document_id": document_id,
                    "status": status,
                    "text_length": len(text),
                    "transactions_found": len(transactions),
                    "metadata": metadata
                }

            except Exception as e:
                # Update status to failed
                await doc_service.update_document_status(
                    doc_id,
                    DOCUMENT_STATUS_FAILED,
                    metadata={"error": str(e)}
                )

                return {
                    "document_id": document_id,
                    "status": "failed",
                    "error": str(e)
                }

    # Run async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(process())


@celery_app.task(name="categorize_transactions", bind=True)
def categorize_transactions(self, transaction_ids: list):
    """
    Celery task: Categorize transactions using ML model.

    Args:
        transaction_ids: List of transaction IDs (UUIDs as strings)

    Returns:
        Dict with categorization results
    """
    from uuid import UUID
    from app.database import async_session_factory
    from app.services.ml_service import ml_service
    from app.core.constants import CATEGORIZATION_CONFIDENCE_THRESHOLD
    from sqlalchemy import select
    from app.models.transaction import Transaction
    import asyncio

    async def process():
        async with async_session_factory() as db:
            categorized_count = 0
            low_confidence_count = 0

            for tx_id_str in transaction_ids:
                tx_id = UUID(tx_id_str)
                
                # Get transaction
                query = select(Transaction).where(Transaction.id == tx_id)
                result = await db.execute(query)
                transaction = result.scalar_one_or_none()

                if not transaction:
                    continue

                # Predict category
                category, confidence = ml_service.predict_category(
                    transaction.description,
                    transaction.merchant
                )

                # Update transaction
                transaction.category = category
                transaction.confidence_score = Decimal(str(confidence))

                # Flag low confidence
                if confidence < CATEGORIZATION_CONFIDENCE_THRESHOLD:
                    low_confidence_count += 1

                categorized_count += 1

            await db.commit()

            return {
                "transaction_ids": transaction_ids,
                "status": "completed",
                "categorized": categorized_count,
                "low_confidence": low_confidence_count
            }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(process())


@celery_app.task(name="detect_transaction_anomalies", bind=True)
def detect_transaction_anomalies(self, user_id: str, date_from: str = None, date_to: str = None):
    """
    Celery task: Detect anomalies in transactions using Z-score analysis.

    Args:
        user_id: User ID (UUID as string)
        date_from: Start date (ISO format, optional)
        date_to: End date (ISO format, optional)

    Returns:
        Dict with anomaly detection results
    """
    from uuid import UUID
    from datetime import datetime
    from decimal import Decimal
    from app.database import async_session_factory
    from app.services.ml_service import ml_service
    from sqlalchemy import select
    from app.models.transaction import Transaction
    import asyncio

    async def process():
        async with async_session_factory() as db:
            # Build query to fetch transactions for the user
            query = select(Transaction).where(Transaction.user_id == UUID(user_id))
            
            # Apply date filters if provided
            if date_from:
                query = query.where(Transaction.date >= datetime.fromisoformat(date_from).date())
            if date_to:
                query = query.where(Transaction.date <= datetime.fromisoformat(date_to).date())
            
            # Order by date for better analysis
            query = query.order_by(Transaction.date)
            
            # Execute query
            result = await db.execute(query)
            transactions = result.scalars().all()
            
            if not transactions:
                return {
                    "user_id": user_id,
                    "status": "completed",
                    "transactions_analyzed": 0,
                    "anomalies_detected": 0,
                    "message": "No transactions found in the specified date range"
                }
            
            # Detect anomalies using ML service
            anomalies = await ml_service.detect_anomalies(transactions, user_id)
            
            # Update transaction records with anomaly flags and Z-scores
            anomaly_count = 0
            for anomaly in anomalies:
                # Find the transaction in the database
                tx_query = select(Transaction).where(Transaction.id == anomaly.transaction_id)
                tx_result = await db.execute(tx_query)
                transaction = tx_result.scalar_one_or_none()
                
                if transaction:
                    transaction.is_anomaly = True
                    transaction.z_score = anomaly.z_score
                    anomaly_count += 1
            
            # Commit all updates
            await db.commit()
            
            return {
                "user_id": user_id,
                "status": "completed",
                "transactions_analyzed": len(transactions),
                "anomalies_detected": anomaly_count,
                "date_from": date_from,
                "date_to": date_to
            }

    # Run async function
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(process())



@celery_app.task(name="generate_spending_forecast", bind=True)
def generate_spending_forecast(self, user_id: str, category: str, periods: list):
    """
    Celery task: Generate spending forecast.

    Args:
        user_id: User ID (UUID as string)
        category: Transaction category (optional)
        periods: List of forecast periods in months

    Returns:
        Dict with forecast results
    """
    # Placeholder - will implement in Task 9
    return {
        "user_id": user_id,
        "status": "pending",
        "message": "Forecasting not yet implemented"
    }


@celery_app.task(name="embed_document_chunks", bind=True)
def embed_document_chunks(self, document_id: str, text: str):
    """
    Celery task: Generate embeddings for document chunks.

    Args:
        document_id: Document ID (UUID as string)
        text: Document text to embed

    Returns:
        Dict with embedding results
    """
    # Placeholder - will implement in Task 11
    return {
        "document_id": document_id,
        "status": "pending",
        "message": "Embedding not yet implemented"
    }

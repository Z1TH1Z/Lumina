"""Document upload and processing API routes."""

import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.transaction import Transaction, TransactionCategory
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.api.dependencies import get_current_user
from app.services.ingestion import process_document
from app.services.categorization import classify_transaction
from app.services.rag import index_document

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a financial document for processing."""
    # Validate file type
    allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not supported")

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        status=DocumentStatus.PROCESSING.value,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Process document (synchronous for now; use Celery for production)
    try:
        result = process_document(file_path)

        doc.raw_text = result.get("raw_text", "")
        doc.parsed_data = json.dumps(result.get("transactions", []))
        doc.page_count = result.get("page_count", 0)
        doc.transaction_count = result.get("transaction_count", 0)
        doc.status = DocumentStatus.COMPLETED.value
        doc.processed_at = datetime.now(timezone.utc)

        # Create transactions from parsed data
        for txn_data in result.get("transactions", []):
            classification = classify_transaction(
                description=txn_data.get("description", ""),
                merchant=txn_data.get("merchant"),
                amount=txn_data.get("amount", 0),
            )

            # Parse date
            try:
                txn_date = datetime.fromisoformat(txn_data.get("date", ""))
            except (ValueError, TypeError):
                txn_date = datetime.now(timezone.utc)

            try:
                cat_value = classification["category"]
            except (ValueError, KeyError):
                cat_value = "other"

            txn = Transaction(
                user_id=current_user.id,
                document_id=doc.id,
                date=txn_date,
                description=txn_data.get("description", ""),
                merchant=txn_data.get("merchant", ""),
                amount=txn_data.get("amount", 0),
                category=cat_value,
                category_confidence=classification.get("confidence"),
                raw_text=txn_data.get("description", ""),
            )
            db.add(txn)

        # Index for RAG
        if doc.raw_text:
            await index_document(doc.id, doc.raw_text, {"filename": file.filename})

        await db.commit()

    except Exception as e:
        await db.rollback()
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)
        db.add(doc)
        await db.commit()

    return DocumentUploadResponse(
        id=doc.id,
        filename=file.filename,
        status=doc.status,
        message=f"Processed {doc.transaction_count} transactions" if doc.status == DocumentStatus.COMPLETED.value else f"Processing failed: {doc.error_message}",
    )


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all user documents."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific document."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its transactions."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete the file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.commit()

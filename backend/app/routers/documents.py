"""Document upload and processing API routes."""

import os
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.transaction import Transaction, TransactionCategory
from app.schemas.document import DocumentResponse, DocumentUploadResponse, EncryptionCheckResponse
from app.api.dependencies import get_current_user
from app.services.ingestion import process_document, check_pdf_encrypted
from app.services.categorization import classify_transaction
from app.services.rag import index_document

router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()


@router.post("/check-encryption", response_model=EncryptionCheckResponse)
async def check_document_encryption(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF and check whether it is password-protected.

    If encrypted, the file is kept on disk so the client can re-submit
    with a password using the returned ``file_id``.
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files can be checked for encryption")

    # Save file to a staging area
    staging_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id), "_staging")
    os.makedirs(staging_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_path = os.path.join(staging_dir, f"{file_id}.pdf")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Check encryption
    encrypted = check_pdf_encrypted(file_path)

    # If not encrypted, leave the file for the subsequent upload call
    return EncryptionCheckResponse(
        encrypted=encrypted,
        file_id=file_id,
        filename=file.filename,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(None),
    password: str = Form(None),
    file_id: str = Form(None),
    original_filename: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a financial document for processing.

    Two usage modes:

    1. **Fresh upload** – send the ``file`` field (optionally with ``password``).
    2. **Staged upload** – provide ``file_id`` from a prior ``/check-encryption``
       call together with the ``password``.  The file is already on disk.

    The password is **never** persisted to the database or logs.
    """

    # ── Resolve the file on disk ────────────────────────────────────────
    staging_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id), "_staging")

    if file_id:
        # Staged file from check-encryption
        staged_path = os.path.join(staging_dir, f"{file_id}.pdf")
        if not os.path.exists(staged_path):
            raise HTTPException(status_code=404, detail="Staged file not found. Please re-upload.")

        # Move staged file to final upload dir
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = ".pdf"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        os.rename(staged_path, file_path)

        content_size = os.path.getsize(file_path)
        actual_filename = original_filename or f"{file_id}.pdf"
        content_type = "application/pdf"
    elif file:
        # Fresh upload
        allowed_types = [
            "application/pdf", "image/png", "image/jpeg", "image/tiff", 
            "text/markdown", "text/plain",
            "application/vnd.ms-excel", # .xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # .xlsx
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not supported")

        upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        content_size = len(content)
        actual_filename = file.filename
        content_type = file.content_type
    else:
        raise HTTPException(status_code=400, detail="Either file or file_id must be provided")

    # ── Create document record ──────────────────────────────────────────
    doc = Document(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=actual_filename,
        file_path=file_path,
        file_size=content_size,
        mime_type=content_type if not file_id else "application/pdf",
        status=DocumentStatus.PROCESSING.value,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # ── Process document (synchronous; use Celery for production) ──────
    encrypted = False
    try:
        # Detect encryption
        if file_path.lower().endswith(".pdf"):
            encrypted = check_pdf_encrypted(file_path)

        if encrypted and not password:
            # Should not happen with the normal frontend flow, but
            # guard against direct API usage.
            doc.status = DocumentStatus.FAILED.value
            doc.error_message = "PDF is encrypted. Please provide a password."
            await db.commit()
            return DocumentUploadResponse(
                id=doc.id,
                filename=actual_filename,
                status=doc.status,
                message="PDF is encrypted. Please provide a password.",
                encrypted=True,
            )

        result = process_document(file_path, password=password if encrypted else None)

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
                # Try common bank statement formats: DD/MM/YY, DD/MM/YYYY
                raw_date = txn_data.get("date", "")
                txn_date = None
                for fmt in ("%d/%m/%y", "%d/%m/%Y", "%m/%d/%Y", "%m/%d/%y"):
                    try:
                        txn_date = datetime.strptime(raw_date, fmt)
                        break
                    except (ValueError, TypeError):
                        continue
                if txn_date is None:
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
            await index_document(doc.id, doc.raw_text, {"filename": actual_filename})

        await db.commit()

    except ValueError as e:
        # Wrong password or decryption failure
        await db.rollback()
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)
        db.add(doc)
        await db.commit()
        return DocumentUploadResponse(
            id=doc.id,
            filename=actual_filename,
            status=doc.status,
            message=str(e),
            encrypted=encrypted,
        )

    except Exception as e:
        await db.rollback()
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)
        db.add(doc)
        await db.commit()

    return DocumentUploadResponse(
        id=doc.id,
        filename=actual_filename,
        status=doc.status,
        message=f"Processed {doc.transaction_count} transactions" if doc.status == DocumentStatus.COMPLETED.value else f"Processing failed: {doc.error_message}",
        encrypted=encrypted,
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

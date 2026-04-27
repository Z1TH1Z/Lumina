"""RAG (Retrieval-Augmented Generation) pipeline service."""

import json
import logging
import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import get_settings
from app.services.llm import llm_service
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document, DocumentStatus
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory document store (production would use FAISS)
_document_store: list[dict] = []
_embeddings_cache: dict[str, list[float]] = {}


def clear_index() -> None:
    """Reset the in-memory index so it can be rebuilt safely."""
    _document_store.clear()
    _embeddings_cache.clear()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = sum(a ** 2 for a in vec_a) ** 0.5
    magnitude_b = sum(b ** 2 for b in vec_b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


async def index_document(
    doc_id: int,
    text: str,
    metadata: dict = None,
    transactions: list[dict] = None,
    user_id: Optional[int] = None,
):
    """Chunk and index a document for RAG retrieval."""
    chunks = []
    
    # 1. Index raw text chunks
    if text:
        chunks.extend(chunk_text(text))

    # 2. Index categorized transactions as individual high-signal chunks
    if transactions:
        for txn in transactions:
            # Format: [Category: Food] 2024-03-25 Swiggy 450.0
            date_str = txn.get("date", "Unknown Date")
            desc = txn.get("description", "No description")
            raw_amt = txn.get("amount", 0.0)
            cat = str(txn.get("category") or "other")
            merchant = txn.get("merchant", "")

            try:
                amt = float(raw_amt)
            except (TypeError, ValueError):
                amt = 0.0
            
            txn_text = f"[Category: {cat.title()}] {date_str} {merchant or desc} {amt}"
            chunks.append(txn_text)

    effective_metadata = {**(metadata or {})}
    if user_id is not None:
        effective_metadata["user_id"] = user_id

    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_{i}"
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()

        # Generate embedding
        embeddings = await llm_service.generate_embeddings([chunk])
        embedding = embeddings[0] if embeddings else []

        _document_store.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "chunk_index": i,
            "text": chunk,
            "hash": chunk_hash,
            "embedding": embedding,
            "metadata": effective_metadata,
        })

    logger.info(f"Indexed document {doc_id}: {len(chunks)} chunks (including {len(transactions or [])} transactions)")


async def rebuild_index_from_db(db: AsyncSession) -> dict:
    """Rebuild the in-memory index from documents stored in the database."""
    clear_index()

    result = await db.execute(
        select(Document).where(Document.status == DocumentStatus.COMPLETED.value)
    )
    documents = result.scalars().all()

    indexed_docs = 0
    indexed_chunks_before = 0

    for doc in documents:
        transactions = []
        if doc.parsed_data:
            try:
                transactions = json.loads(doc.parsed_data)
            except json.JSONDecodeError:
                logger.warning("Could not parse stored transactions for document %s", doc.id)

        await index_document(
            doc_id=doc.id,
            text=doc.raw_text or "",
            metadata={"filename": doc.original_filename},
            transactions=transactions,
            user_id=doc.user_id,
        )
        indexed_docs += 1

    return {
        "documents_indexed": indexed_docs,
        "chunks_indexed": len(_document_store) - indexed_chunks_before,
    }


async def search(
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
    user_id: Optional[int] = None,
) -> list[dict]:
    """Search for relevant document chunks."""
    if not _document_store:
        return []

    # Generate query embedding
    query_embeddings = await llm_service.generate_embeddings([query])
    query_embedding = query_embeddings[0] if query_embeddings else []

    results = []

    # Try embedding-based search if we have a valid query embedding
    if query_embedding and not all(v == 0 for v in query_embedding):
        for doc in _document_store:
            if user_id is not None and doc.get("metadata", {}).get("user_id") != user_id:
                continue
            doc_embedding = doc.get("embedding", [])
            # Skip docs with zero/empty embeddings
            if not doc_embedding or all(v == 0 for v in doc_embedding):
                continue
            sim = cosine_similarity(query_embedding, doc_embedding)
            if sim >= threshold:
                results.append({
                    "chunk_id": doc["chunk_id"],
                    "doc_id": doc["doc_id"],
                    "text": doc["text"],
                    "similarity": round(sim, 4),
                    "metadata": doc.get("metadata", {}),
                })

    # Always fall back to keyword search if embedding search found nothing
    if not results:
        results = _keyword_search(query, top_k, user_id=user_id)

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def _keyword_search(query: str, top_k: int = 5, user_id: Optional[int] = None) -> list[dict]:
    """Fallback keyword-based search."""
    query_words = set(query.lower().split())
    results = []

    for doc in _document_store:
        if user_id is not None and doc.get("metadata", {}).get("user_id") != user_id:
            continue
        text_words = set(doc["text"].lower().split())
        overlap = len(query_words & text_words)
        if overlap > 0:
            score = overlap / len(query_words)
            results.append({
                "chunk_id": doc["chunk_id"],
                "doc_id": doc["doc_id"],
                "text": doc["text"],
                "similarity": round(score, 4),
                "metadata": doc.get("metadata", {}),
            })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


async def _get_user_spending_summary(db: AsyncSession, user_id: int) -> str:
    """Fetch a high-level spending summary for the user."""
    try:
        # Get top 5 categories
        result = await db.execute(
            select(Transaction.category, func.sum(Transaction.amount).label("total"))
            .where(Transaction.user_id == user_id, Transaction.amount < 0)
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).asc()) # Most negative first
            .limit(5)
        )
        summaries = result.all()
        
        if not summaries:
            return ""

        summary_parts = ["--- USER SPENDING SUMMARY (Top 5 Categories) ---"]
        for cat, total in summaries:
            cat_label = str(cat or "other").title()
            total_value = abs(float(total or 0))
            summary_parts.append(f"- {cat_label}: {total_value:.2f}")
        
        return "\n".join(summary_parts) + "\n\n"
    except Exception as e:
        logger.error(f"Error generating spending summary: {e}")
        return ""


async def query_with_rag(
    question: str,
    system_context: str = "",
    top_k: int = 5,
    db: Optional[AsyncSession] = None,
    session_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    """Full RAG pipeline: search → retrieve → generate answer with citations."""
    # 1. Search for relevant chunks
    relevant_chunks = await search(question, top_k=top_k, user_id=user_id)

    # 1.2 Fetch spending summary if we have DB and User
    spending_summary = ""
    if db and user_id:
        spending_summary = await _get_user_spending_summary(db, user_id)

    # 1.5 Fetch Chat History
    history_context = ""
    if db and session_id:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = result.scalars().all()
        if messages:
            messages.reverse()
            hist_parts = []
            for m in messages:
                role = "User" if m.role == "user" else "Assistant"
                hist_parts.append(f"{role}: {m.content}")
            history_context = "--- PREVIOUS CONVERSATION HISTORY ---\n" + "\n".join(hist_parts) + "\n\n"

    # 2. Build context from retrieved chunks
    if relevant_chunks:
        context_parts = []
        citations = []
        for i, chunk in enumerate(relevant_chunks):
            context_parts.append(f"[Source {i+1}] {chunk['text']}")
            citations.append({
                "source_id": i + 1,
                "doc_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "similarity": chunk["similarity"],
                "excerpt": chunk["text"][:200],
            })
        context = "\n\n".join(context_parts)
    else:
        context = "No relevant documents found."
        citations = []

    # 3. Generate answer with LLM
    prompt = f"""Based on the following financial documents, answer the user's question.
Always cite your sources using [Source N] notation.
If the documents don't contain enough information to answer, say so clearly.

--- DOCUMENTS ---
{context}

{spending_summary}

{history_context}--- CURRENT QUESTION ---
{question}

--- INSTRUCTIONS ---
{system_context}
Provide a clear, specific answer. Cite all sources used."""

    system_prompt = (
        "You are a financial analysis assistant. Answer questions based only on the provided documents and the spending summary. "
        "The documents include system-assigned categories in brackets like [Category: Shopping]. "
        "Always cite sources using [Source N] and refer to the 'USER SPENDING SUMMARY' for aggregate category data. "
        "Never make up information. If you're unsure, say so."
    )

    if await llm_service.is_available():
        answer = await llm_service.generate(prompt, system_prompt=system_prompt)
        confidence = max((c["similarity"] for c in citations), default=0)
    else:
        if relevant_chunks:
            answer = f"Based on your documents, here are the most relevant excerpts:\n\n"
            for i, chunk in enumerate(relevant_chunks):
                answer += f"[Source {i+1}] {chunk['text'][:300]}...\n\n"
            answer += "\n*(Full LLM analysis unavailable - Ollama not connected)*"
        else:
            if _document_store:
                answer = "I couldn't find any exact keyword matches for your query in the uploaded documents.\n\n*(Note: Advanced AI semantic search is currently disabled because Ollama is not running on port 11434. Please start Ollama to enable conversational queries!)*"
            else:
                answer = "No relevant documents found for your query. Please upload financial documents first."
        confidence = 0

    # 4. Hallucination check
    hallucination_warning = None
    if confidence < 0.3 and relevant_chunks:
        hallucination_warning = "Low confidence: The answer may not be well-supported by the documents."

    # 5. Save to database
    if db and session_id:
        user_msg = ChatMessage(session_id=session_id, role="user", content=question)
        asst_msg = ChatMessage(
            session_id=session_id, 
            role="assistant", 
            content=answer,
            sources_json=json.dumps(citations) if citations else None
        )
        db.add_all([user_msg, asst_msg])
        await db.flush()

    return {
        "answer": answer,
        "citations": citations,
        "confidence": round(confidence, 4),
        "hallucination_warning": hallucination_warning,
        "chunks_retrieved": len(relevant_chunks),
    }


def get_index_stats() -> dict:
    """Return current index statistics."""
    doc_ids = set(d["doc_id"] for d in _document_store)
    return {
        "total_chunks": len(_document_store),
        "total_documents": len(doc_ids),
        "document_ids": list(doc_ids),
    }

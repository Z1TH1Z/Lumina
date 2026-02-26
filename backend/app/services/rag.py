"""RAG (Retrieval-Augmented Generation) pipeline service."""

import os
import json
import logging
import hashlib
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.services.llm import llm_service
from app.models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()

# In-memory document store (production would use FAISS)
_document_store: list[dict] = []
_embeddings_cache: dict[str, list[float]] = {}


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


async def index_document(doc_id: int, text: str, metadata: dict = None):
    """Chunk and index a document for RAG retrieval."""
    chunks = chunk_text(text)

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
            "metadata": metadata or {},
        })

    logger.info(f"Indexed document {doc_id}: {len(chunks)} chunks")


async def search(query: str, top_k: int = 5, threshold: float = 0.3) -> list[dict]:
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
        results = _keyword_search(query, top_k)

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def _keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """Fallback keyword-based search."""
    query_words = set(query.lower().split())
    results = []

    for doc in _document_store:
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


async def query_with_rag(
    question: str,
    system_context: str = "",
    top_k: int = 5,
    db: Optional[AsyncSession] = None,
    session_id: Optional[int] = None,
) -> dict:
    """Full RAG pipeline: search → retrieve → generate answer with citations."""
    # 1. Search for relevant chunks
    relevant_chunks = await search(question, top_k=top_k)

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

{history_context}--- CURRENT QUESTION ---
{question}

--- INSTRUCTIONS ---
{system_context}
Provide a clear, specific answer. Cite all sources used."""

    system_prompt = (
        "You are a financial analysis assistant. Answer questions based only on the provided documents. "
        "Always cite sources. Never make up information. If you're unsure, say so."
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

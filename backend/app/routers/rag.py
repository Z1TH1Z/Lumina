"""RAG (Retrieval-Augmented Generation) API routes."""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.transaction import Transaction
from app.schemas.chat import (
    ChatSessionCreate, 
    ChatSessionResponse, 
    ChatSessionListResponse, 
    ChatMessageResponse
)
from app.api.dependencies import get_current_user
from app.services.rag import query_with_rag, get_index_stats
from app.services.pii import sanitize_for_llm

router = APIRouter(prefix="/rag", tags=["RAG Chat"])


class ChatMessagePayload(BaseModel):
    message: str
    context: Optional[str] = None
    session_id: Optional[int] = None

class ToolCallRequest(BaseModel):
    message: str

# --- Chat Session Management ---

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=current_user.id,
        title=session_data.title or "New Chat"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionListResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .where(ChatSession.is_archived == False)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages for a specific chat session."""
    # Verify ownership
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return messages_result.scalars().all()


# --- RAG Endpoints ---


@router.put("/sessions/{session_id}/archive")
async def archive_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a chat session (soft delete — data is preserved)."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_archived = True
    await db.commit()
    return {"message": "Session archived", "id": session_id}


@router.post("/query")
async def rag_query(
    chat: ChatMessagePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query the RAG system with a financial question."""
    # Sanitize PII before processing
    sanitized_message = sanitize_for_llm(chat.message)

    result = await query_with_rag(
        question=sanitized_message,
        system_context=chat.context or "",
        db=db,
        session_id=chat.session_id,
        user_id=current_user.id,
    )

    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "confidence": result["confidence"],
        "hallucination_warning": result.get("hallucination_warning"),
    }


@router.get("/index/stats")
async def index_statistics(
    current_user: User = Depends(get_current_user),
):
    """Get RAG index statistics."""
    return get_index_stats()


@router.get("/nodes")
async def get_graph_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve graph nodes and links for 3D visualization"""
    nodes = []
    links = []

    valid_node_ids = set()
    user_node_id = f"user_{current_user.id}"
    nodes.append({"id": user_node_id, "name": "You", "group": "user", "val": 20})
    valid_node_ids.add(user_node_id)

    # Fetch transactions grouped by category
    result = await db.execute(select(Transaction).where(Transaction.user_id == current_user.id))
    transactions = result.scalars().all()

    categories = set([t.category.value if hasattr(t.category, 'value') else str(t.category) for t in transactions if t.category])
    
    for cat in categories:
        cat_id = f"cat_{cat}"
        nodes.append({"id": cat_id, "name": str(cat).capitalize(), "group": "category", "val": 10})
        valid_node_ids.add(cat_id)

    for t in transactions:
        txn_id = f"txn_{t.id}"
        amount_size = max(1, min(abs(t.amount) / 50, 5))
        
        nodes.append({
            "id": txn_id,
            "name": f"{t.merchant} - ${abs(t.amount):.2f}",
            "group": "transaction",
            "val": amount_size,
        })
        valid_node_ids.add(txn_id)
        
        cat_str = t.category.value if hasattr(t.category, 'value') else str(t.category) if t.category else None
        target_cat_id = f"cat_{cat_str}"
        target_id = target_cat_id if target_cat_id in valid_node_ids else user_node_id
        
        # Determine Direction based on Income (positive) or Expense (negative)
        is_income = t.amount > 0
        
        # For Income: Money flows to You (Txn -> Category -> User)
        # For Expense: Money flows out (User -> Category -> Txn)
        
        # Determine link color
        link_color = "#10b981" if is_income else "#ef4444" 
        
        if is_income:
            # Transaction -> Category -> User
            links.append({"source": txn_id, "target": target_id, "value": 1, "color": link_color})
            
            # Add or update the Category -> User link if not already added 
            # (Just doing it redundantly for visual density is fine since ForceGraph maps it)
            links.append({"source": target_id, "target": user_node_id, "value": 5, "color": link_color})
        else:
            # User -> Category -> Transaction
            links.append({"source": user_node_id, "target": target_id, "value": 5, "color": link_color})
            links.append({"source": target_id, "target": txn_id, "value": 1, "color": link_color})
            
        
    # RAG Docs
    stats = get_index_stats()
    if stats.get("total_documents", 0) > 0 and len(transactions) > 0:
        rag_id = "rag_brain"
        nodes.append({"id": rag_id, "name": "AI Memory", "group": "ai", "val": 15})
        valid_node_ids.add(rag_id)
        links.append({"source": rag_id, "target": user_node_id, "value": 5, "color": "#f59e0b"})

        for doc_id in stats.get("document_ids", []):
            doc_node_id = f"doc_{doc_id}"
            nodes.append({"id": doc_node_id, "name": f"Document {doc_id}", "group": "document", "val": 8})
            valid_node_ids.add(doc_node_id)
            links.append({"source": doc_node_id, "target": rag_id, "value": 2, "color": "#3b82f6"})

    return {"nodes": nodes, "links": links}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                await websocket.send_json({"error": "Empty message"})
                continue

            # Sanitize PII
            sanitized_message = sanitize_for_llm(message)

            # Query RAG
            result = await query_with_rag(question=sanitized_message)

            await websocket.send_json({
                "type": "response",
                "answer": result["answer"],
                "citations": result["citations"],
                "confidence": result["confidence"],
                "hallucination_warning": result.get("hallucination_warning"),
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

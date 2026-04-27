from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.database import init_db, engine as async_engine, async_session_factory
from app.services.llm import llm_service
from app.services.rag import rebuild_index_from_db
from sqlalchemy import text
import logging
import os

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Financial Copilot API",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    # Ensure data directory exists
    os.makedirs("./data/uploads", exist_ok=True)
    # Initialize database tables
    await init_db()
    # Rebuild the in-memory RAG index from persisted documents after restarts.
    async with async_session_factory() as session:
        try:
            stats = await rebuild_index_from_db(session)
            logger.info(
                "Rebuilt RAG index on startup: %s documents, %s chunks",
                stats["documents_indexed"],
                stats["chunks_indexed"],
            )
        except Exception:
            logger.exception("Failed to rebuild RAG index on startup")


async def _build_health_response():
    """Build a comprehensive health response checking DB and LLM."""
    # Check database connectivity
    db_status = "disconnected"
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    # Check LLM availability
    llm_available = await llm_service.is_available()

    status = "healthy" if db_status == "connected" else "degraded"

    return {
        "status": status,
        "database": db_status,
        "llm_available": llm_available,
        "version": settings.APP_VERSION,
    }


@app.get("/api/health")
async def health_check():
    return await _build_health_response()


@app.get("/api/v1/health")
async def health_check_v1():
    return await _build_health_response()


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs"
    }

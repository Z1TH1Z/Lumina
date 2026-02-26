from fastapi import APIRouter

from app.routers import auth, documents, transactions, anomalies, forecasting, rag, tools, budgets

api_router = APIRouter()
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(transactions.router, tags=["Transactions"])
api_router.include_router(anomalies.router, tags=["Anomaly Detection"])
api_router.include_router(forecasting.router, tags=["Forecasting"])
api_router.include_router(rag.router, tags=["RAG Chat"])
api_router.include_router(tools.router, tags=["Tools"])
api_router.include_router(budgets.router, tags=["Budgets"])

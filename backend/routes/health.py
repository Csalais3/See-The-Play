# backend/routes/health.py
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "SeeThePlay API",
        "version": "1.0.0"
    }
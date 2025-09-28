# backend/routes/__init__.py
"""
Routes package for SeeThePlay API
Contains all API endpoint routers
"""
from .predictions import router as predictions_router
from .live import router as live_router
from .health import router as health_router

__all__ = ["predictions_router", "live_router", "health_router"]

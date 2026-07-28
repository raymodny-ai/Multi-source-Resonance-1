"""
API routes package — exports all route modules for registration in main.py.
"""

from backend.api.routes.auth import router as auth_router
from backend.api.routes.dashboard import router as dashboard_router
from backend.api.routes.gex import router as gex_router
from backend.api.routes.vix import router as vix_router
from backend.api.routes.crypto import router as crypto_router
from backend.api.routes.darkpool import router as darkpool_router
from backend.api.routes.signals import router as signals_router
from backend.api.routes.system import router as system_router
from backend.api.routes.config import router as config_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.analysis import router as analysis_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "gex_router",
    "vix_router",
    "crypto_router",
    "darkpool_router",
    "signals_router",
    "system_router",
    "config_router",
    "metrics_router",
    "analysis_router",
]

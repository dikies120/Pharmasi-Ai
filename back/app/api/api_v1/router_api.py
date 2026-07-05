from fastapi import APIRouter

from back.app.api.api_v1.endpoints import (
    chat, health, graph,
    monitoring_stok,
    validasi_obat,
    dispensing,
    asuransi,
    reminder,
    informasi_obat,
    analytics,
)
from back.app.routes.auth_routes import router as auth_router
from back.app.routes.pharmacy_routes import router as pharmacy_router
from back.app.routes.admin_routes import router as admin_router
from back.app.routes.simrs_routes import router as simrs_router

router = APIRouter(prefix="/api/v1")

# Auth endpoints
router.include_router(auth_router)

# Admin endpoints
router.include_router(admin_router)

# Pharmacy endpoints
router.include_router(pharmacy_router)

# SIM RS endpoints
router.include_router(simrs_router)

# Existing endpoints
router.include_router(chat.router)
router.include_router(health.router)
router.include_router(graph.router)
router.include_router(monitoring_stok.router)
router.include_router(validasi_obat.router)
router.include_router(dispensing.router)
router.include_router(asuransi.router)
router.include_router(reminder.router)
router.include_router(informasi_obat.router)
router.include_router(analytics.router)

__all__ = ["router"]

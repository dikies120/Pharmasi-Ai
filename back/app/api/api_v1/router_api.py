from fastapi import APIRouter

from back.app.api.api_v1.endpoints import (
    chat, health, graph,
    monitoring_stok,
    validasi_obat,
    dispensing,
    asuransi,
    reminder,
    informasi_obat
)

router = APIRouter(prefix="/api/v1")

router.include_router(chat.router)
router.include_router(health.router)
router.include_router(graph.router)
router.include_router(monitoring_stok.router)
router.include_router(validasi_obat.router)
router.include_router(dispensing.router)
router.include_router(asuransi.router)
router.include_router(reminder.router)
router.include_router(informasi_obat.router)

__all__ = ["router"]

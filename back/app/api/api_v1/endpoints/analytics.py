from fastapi import APIRouter, Depends, HTTPException
import logging
import json
from datetime import datetime, timedelta

from back.app.dependencies import get_mcp_client, get_agent
from back.pharma_mcp.client import MCPClient

from back.app.middleware.auth import require_pharmacist_or_admin
from back.database.pgvektor import get_db_connection
from back.services.graph_data import GraphDataService

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_pharmacist_or_admin)]
)
logger = logging.getLogger(__name__)


def _get_inventory_data(agent, result: dict) -> dict:
    ai_insight = result.get("ai_insight", "")
    inventory_data = result.get("data", {})

    logger.info("[Analytics] Fetching data from GraphDataService")
    
    conn = get_db_connection()
    if conn:
        try:
            gd = GraphDataService.get_medicines_overview(conn)
            if gd:
                return gd
        finally:
            conn.close()

    return {}


def _build_analytics_from_data(data: dict) -> dict:
    from back.core.llm import get_llm
    llm = get_llm()

    total = data.get("total_medicines", 0)
    stock_dist = data.get("stock_distribution", {})
    expiry_dist = data.get("expiry_distribution", {})
    medicines = data.get("medicines", [])

    kritis = stock_dist.get("Kritis (<50)", 0)
    aman = stock_dist.get("Aman (50-200)", 0)
    banyak = stock_dist.get("Banyak (>200)", 0)
    segera_expired = expiry_dist.get("Segera Kadaluarsa (< 30 hari)", 0)
    aman_expired = expiry_dist.get("Aman (> 30 hari)", 0)

    sorted_by_stock = sorted(medicines, key=lambda x: x.get("stok", 0))
    lowest = sorted_by_stock[:3] if sorted_by_stock else []
    highest = sorted_by_stock[-3:][::-1] if sorted_by_stock else []

    def ask_llm(prompt: str, fallback: str) -> str:
        try:
            r = llm.generate(prompt).strip()
            r = r.split(".")[0].strip()
            if len(r) > 10:
                return r
        except Exception:
            pass
        return fallback

    # Deskriptif
    temuan = []

    if total > 0:
        temuan.append(
            f"Total {total} jenis obat terdaftar: {kritis} kritis, {aman} aman, {banyak} stok banyak "
            f"(Kritis: {kritis}, Aman: {aman})"
        )
    if lowest:
        names = ", ".join(m.get("nama_obat", "-") for m in lowest[:2])
        stocks = ", ".join(str(m.get("stok", 0)) for m in lowest[:2])
        temuan.append(f"Obat dengan stok terendah: {names} (Stok: {stocks} unit)")
    if segera_expired > 0:
        temuan.append(
            f"{segera_expired} batch obat akan kadaluarsa dalam 30 hari ke depan "
            f"(Batch expired: {segera_expired})"
        )
    elif aman_expired > 0:
        temuan.append(f"Semua {aman_expired} batch obat masih aman dari kadaluarsa (Batch aman: {aman_expired})")

    # Prediktif 
    proyeksi = []

    if kritis > 0:
        proyeksi.append(
            f"{kritis} jenis obat berisiko habis dalam 30 hari jika tidak di-restock "
            f"(Kritis: {kritis} jenis)"
        )
    if segera_expired > 0:
        proyeksi.append(
            f"{segera_expired} batch akan expired bulan ini, perlu rotasi stok segera "
            f"(Batch: {segera_expired})"
        )
    if highest:
        names = ", ".join(m.get("nama_obat", "-") for m in highest[:2])
        proyeksi.append(
            f"Obat {names} memiliki stok tinggi, pantau agar tidak menumpuk "
            f"(Stok: {', '.join(str(m.get('stok',0)) for m in highest[:2])} unit)"
        )

    # Preskriptif
    aksi = []

    if kritis > 0:
        low_names = ", ".join(m.get("nama_obat", "-") for m in lowest[:2])
        aksi.append(f"Segera restock {low_names} — stok di bawah 50 unit")
    if segera_expired > 0:
        aksi.append(f"Prioritaskan dispensing {segera_expired} batch yang mendekati expired bulan ini")
    if total > 0:
        aksi.append(f"Lakukan audit stok mingguan untuk {kritis} obat kritis dari total {total} jenis")

    if not temuan:
        temuan = ["Data inventory belum tersedia — isi tabel inventory_batches terlebih dahulu"]
    if not proyeksi:
        proyeksi = ["Proyeksi akan tersedia setelah data inventory diisi"]
    if not aksi:
        aksi = ["Masukkan data obat ke sistem untuk mendapatkan rekomendasi aksi"]

    return {
        "deskriptif": {"temuan": temuan[:3]},
        "prediktif": {"proyeksi": proyeksi[:3]},
        "preskriptif": {"aksi": aksi[:3]},
    }


@router.get("/insights")
async def get_analytics_insights(mcp_client: MCPClient = Depends(get_mcp_client)):
    try:
        agent = get_agent()
        logger.info("[Analytics] Agent calling MCP: get_inventory_analytics")
        result = await agent.run_monitoring_analytics(mcp_client)

        inventory_data = _get_inventory_data(agent, result)
        logger.info(f"[Analytics] Data: total_medicines={inventory_data.get('total_medicines', 0)}")

        analytics = _build_analytics_from_data(inventory_data)

        logger.info("[Analytics] Analytics built successfully")
        return {"status": "success", "analytics": analytics}

    except Exception as e:
        logger.error(f"[Analytics] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

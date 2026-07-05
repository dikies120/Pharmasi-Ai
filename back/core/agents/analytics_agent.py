import json
import logging
from typing import Dict, Any, List, Optional
from back.core.llm import get_llm
from back.core.agents.base_agent import BaseAgent
from back.core.prompts import VALIDATION_PROMPT, DISPENSING_PROMPT, DISPENSING_RETRY_PROMPT

logger = logging.getLogger(__name__)
llm = get_llm()

class AnalyticsAgent(BaseAgent):
    async def run_monitoring_analytics(self, mcp_client: Any) -> Dict[str, Any]:
        result = await self._call_tool_json(mcp_client, "get_inventory_analytics", {})
        if not result:
            result = {"status": "success", "data": {}}

        inventory_data = result.get("data", {}) if isinstance(result, dict) else {}

        stok_data = inventory_data.get("stok", {})
        transaksi_data = inventory_data.get("transaksi", {})
        top_selling = inventory_data.get("penjualan", {}).get("top_selling", [])

        stok_tertinggi = stok_data.get("tertinggi") or {}
        stok_terendah = stok_data.get("terendah") or {}
        hampir_habis = stok_data.get("hampir_habis", [])

        top_lines = []
        for idx, item in enumerate(top_selling[:5], start=1):
            top_lines.append(f"{idx}. {item.get('nama', '-')} = {item.get('total_terjual', 0)}")
        top_block = "\n".join(top_lines) if top_lines else "-"

        ai_insight = (
            f"stok tertinggi obat = {stok_tertinggi.get('nama', '-')} ({stok_tertinggi.get('stok', 0)})\n"
            f"stok terendah obat = {stok_terendah.get('nama', '-')} ({stok_terendah.get('stok', 0)})\n"
            f"total jenis obat = {stok_data.get('total_jenis_obat', 0)}\n"
            f"jumlah obat stok kritis (<50) = {len(hampir_habis)}\n"
            f"pendapatan bulan ini = Rp {float(transaksi_data.get('pendapatan_bulan_ini', 0)):,.0f}\n"
            f"transaksi bulan ini = {int(transaksi_data.get('transaksi_bulan_ini', 0))}\n"
            f"total transaksi = {int(transaksi_data.get('jumlah', 0))}\n"
            f"total pendapatan = Rp {float(transaksi_data.get('revenue', 0)):,.0f}\n"
            f"top obat terjual =\n{top_block}"
        )

        result["ai_insight"] = ai_insight
        return result


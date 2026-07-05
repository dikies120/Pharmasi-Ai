import logging
from typing import Dict, Any
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class GraphDataService:

    @staticmethod
    def get_medicines_overview(pg_conn) -> Dict[str, Any]:
        try:
            today = date.today()
            soon = today + timedelta(days=30)

            with pg_conn.cursor() as cur:
                # Inventory dari inventory_batches (pakai nama_obat langsung)
                cur.execute("""
                    SELECT
                        ib.nama_obat,
                        COALESCE(SUM(ib.stock_qty), 0) AS stok,
                        MIN(ib.expiry_date)             AS expiry
                    FROM inventory_batches ib
                    GROUP BY ib.nama_obat
                    ORDER BY ib.nama_obat ASC
                """)
                inventory_rows = cur.fetchall()

                # Stock movements (nama_obat, type, qty)
                cur.execute("""
                    SELECT nama_obat, type, SUM(qty) AS total_moved
                    FROM stock_movements
                    GROUP BY nama_obat, type
                    ORDER BY total_moved DESC
                """)
                movement_rows = cur.fetchall()

            medicines = []
            stock_dist = {"Kritis (<50)": 0, "Aman (50-200)": 0, "Banyak (>200)": 0}
            expiry_dist = {"Segera Kadaluarsa (< 30 hari)": 0, "Aman (> 30 hari)": 0}

            for nama_obat, stok, expiry in inventory_rows:
                stok = int(stok) if stok else 0
                if stok < 50:
                    stock_dist["Kritis (<50)"] += 1
                elif stok <= 200:
                    stock_dist["Aman (50-200)"] += 1
                else:
                    stock_dist["Banyak (>200)"] += 1

                if expiry:
                    if expiry <= soon:
                        expiry_dist["Segera Kadaluarsa (< 30 hari)"] += 1
                    else:
                        expiry_dist["Aman (> 30 hari)"] += 1

                medicines.append({
                    "nama_obat": nama_obat,
                    "stok": stok,
                    "tanggal_kadaluarsa": str(expiry) if expiry else "-",
                })

            movement_data = [
                {"nama_obat": r[0], "tipe": r[1], "jumlah": r[2]}
                for r in movement_rows
            ]

            return {
                "total_medicines": len(medicines),
                "stock_distribution": stock_dist,
                "expiry_distribution": expiry_dist,
                "medicines": medicines,
                "movements_analytics": movement_data,
            }

        except Exception as e:
            logger.error(f"Error get_medicines_overview: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_chat_history_trends(memory_manager) -> Dict[str, Any]:
        return {"total_chats": 0}

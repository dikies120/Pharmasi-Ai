import logging
from typing import Dict, Any
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class GraphDataService:
    @staticmethod
    def get_medicines_overview(pg_conn) -> Dict[str, Any]:
        try:
            # REAL-TIME INVENTORY
            sql_inventory = """
                SELECT m.name, sum(b.stock_qty), min(b.expiry_date)
                FROM inventory_batches b 
                JOIN medications m ON m.id = b.medication_id
                GROUP BY m.name
                ORDER BY m.name ASC
            """
            
            # DESCRIPTIVE ANALYTICS - SALES (Pola Penjualan)
            sql_sales = """
                SELECT m.name, SUM(si.qty) as total_sold, SUM(si.subtotal) as total_revenue
                FROM sales_items si
                JOIN medications m ON m.id = si.medication_id
                GROUP BY m.name
                ORDER BY total_sold DESC
            """
            
            # DESCRIPTIVE ANALYTICS - MOVEMENTS (Pergerakan Obat)
            sql_movements = """
                SELECT m.name, sm.type, SUM(sm.qty) as total_moved
                FROM stock_movements sm
                JOIN medications m ON m.id = sm.medication_id
                GROUP BY m.name, sm.type
                ORDER BY total_moved DESC
            """
            
            with pg_conn.cursor() as cur:
                cur.execute(sql_inventory)
                inventory_rows = cur.fetchall()
                
                cur.execute(sql_sales)
                sales_rows = cur.fetchall()
                
                cur.execute(sql_movements)
                movement_rows = cur.fetchall()
            
            # Prepare Inventory Data
            medicines = []
            stock_dist = {"Kritis (<50)": 0, "Aman (50-200)": 0, "Banyak (>200)": 0}
            expiry_dist = {"Segera Kadaluarsa (< 30 hari)": 0, "Aman (> 30 hari)": 0}
            
            today = datetime.now().date()
            soon = today + __import__('datetime').timedelta(days=30)
            
            for name, stok, expiry in inventory_rows:
                if stok < 50: stock_dist["Kritis (<50)"] += 1
                elif stok < 200: stock_dist["Aman (50-200)"] += 1
                else: stock_dist["Banyak (>200)"] += 1
                
                if expiry:
                    if expiry <= soon: expiry_dist["Segera Kadaluarsa (< 30 hari)"] += 1
                    else: expiry_dist["Aman (> 30 hari)"] += 1
                    
                medicines.append({"nama_obat": name, "stok": stok, "tanggal_kadaluarsa": str(expiry)})

            # Prepare Sales Data
            sales_data = [{"nama_obat": r[0], "terjual": r[1], "pendapatan": float(r[2])} for r in sales_rows]
            
            # Prepare Movements Data
            movement_data = [{"nama_obat": r[0], "tipe": r[1], "jumlah": r[2]} for r in movement_rows]

            return {
                "total_medicines": len(medicines),
                "stock_distribution": stock_dist,
                "expiry_distribution": expiry_dist,
                "medicines": medicines,
                "sales_analytics": sales_data,
                "movements_analytics": movement_data
            }
        
        except Exception as e:
            logger.error(f"Error getting medicines overview: {str(e)}", exc_info=True)
            return {}

    @staticmethod
    def get_chat_history_trends(memory_manager) -> Dict[str, Any]:
        return {} # Optional logic

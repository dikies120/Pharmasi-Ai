import logging
from datetime import date

logger = logging.getLogger(__name__)

def get_realtime_stock_tool(pg_conn, nama_obat: str = None, lokasi: str = None, status: str = None) -> dict:
    with pg_conn.cursor() as cur:
        query = """
            SELECT 
                '' as kfa_code, b.nama_obat as name, '' as form, 
                l.name as location_name, 
                b.batch_no, b.expiry_date, b.stock_qty, b.unit
            FROM inventory_batches b
            JOIN locations l ON l.id = b.location_id
            WHERE 1=1
        """
        params = []
        if nama_obat and nama_obat.strip():
            query += " AND b.nama_obat ILIKE %s"
            params.append(f"%{nama_obat}%")
        if lokasi and lokasi != "Semua Lokasi":
            query += " AND l.name = %s"
            params.append(lokasi)
            
        cur.execute(query, params)
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            qty = row[6]
            expiry_date = row[5]

            days_to_expiry = None
            near_expiry = False
            if expiry_date:
                try:
                    days_to_expiry = (expiry_date - date.today()).days
                    near_expiry = days_to_expiry <= 30
                except Exception:
                    days_to_expiry = None
                    near_expiry = False

            current_status = "Aman"
            if qty < 50:
                current_status = "Stok Kritis"
            elif qty < 100:
                current_status = "Hampir Habis"
                
            if status and status != "Semua":
                status_norm = str(status).strip().lower()
                if status_norm == "stok kritis" and current_status != "Stok Kritis":
                    continue
                if status_norm == "aman" and current_status != "Aman":
                    continue
                if status_norm == "hampir habis" and current_status != "Hampir Habis":
                    continue
                if status_norm in {"hampir expired", "hampir kadaluarsa"} and not near_expiry:
                    continue
            
            results.append({
                "kfa_code": row[0],
                "nama_obat": row[1],
                "bentuk": row[2],
                "lokasi": row[3],
                "batch_no": row[4],
                "expiry_date": row[5].strftime("%Y-%m-%d") if row[5] else None,
                "days_to_expiry": days_to_expiry,
                "near_expiry": near_expiry,
                "stok": qty,
                "satuan": row[7],
                "status": current_status
            })
        return {"status": "success", "data": results}

def get_inventory_analytics_tool(pg_conn) -> dict:
    with pg_conn.cursor() as cur:
        # 1. Stok (Overstock, Understock, Movements)
        cur.execute("""
            SELECT b.nama_obat as name, SUM(b.stock_qty) as total_qty
            FROM inventory_batches b
            GROUP BY b.nama_obat ORDER BY total_qty ASC
        """)
        all_stock = cur.fetchall()
        hampir_habis = [{"nama": r[0], "stok": r[1]} for r in all_stock if r[1] < 50]
        overstock = [{"nama": r[0], "stok": r[1]} for r in all_stock if r[1] > 300]
        stok_terendah = {"nama": all_stock[0][0], "stok": all_stock[0][1]} if all_stock else None
        stok_tertinggi = {"nama": all_stock[-1][0], "stok": all_stock[-1][1]} if all_stock else None
        
        cur.execute("""
            SELECT sm.nama_obat as name, 
                   SUM(CASE WHEN sm.type = 'IN' THEN sm.qty ELSE 0 END) as total_in,
                   SUM(CASE WHEN sm.type = 'OUT' THEN sm.qty ELSE 0 END) as total_out
            FROM stock_movements sm
            GROUP BY sm.nama_obat ORDER BY total_out DESC LIMIT 5
        """)
        movements = [{"nama": r[0], "masuk": r[1], "keluar": r[2]} for r in cur.fetchall()]

        # 2. Penjualan (Laris, Jarang Dipakai)
        cur.execute("""
            SELECT si.nama_obat as name, SUM(si.qty) as total_qty, SUM(si.subtotal) as total_revenue
            FROM sales_items si
            GROUP BY si.nama_obat ORDER BY total_qty DESC
        """)
        all_sales = cur.fetchall()
        top_selling = [{"nama": r[0], "total_terjual": r[1], "pendapatan": float(r[2])} for r in all_sales[:5]]
        jarang_dipakai = [{"nama": r[0], "total_terjual": r[1]} for r in all_sales[-5:]] if len(all_sales) > 5 else []

        # 3. Transaksi
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(total_amount), 0), COALESCE(AVG(total_amount), 0)
            FROM sales
        """)
        tx_row = cur.fetchone()
        transactions = {"jumlah": tx_row[0], "revenue": float(tx_row[1]), "avg_order": float(tx_row[2])}

        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0), COUNT(*)
            FROM sales
            WHERE DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE)
        """)
        month_row = cur.fetchone()
        transactions["pendapatan_bulan_ini"] = float(month_row[0] or 0)
        transactions["transaksi_bulan_ini"] = int(month_row[1] or 0)

        # 4. User / Pasien
        cur.execute("""
            SELECT p.name, COUNT(pr.id) as kunjungan
            FROM prescriptions pr JOIN patients p ON p.id = pr.patient_id
            GROUP BY p.name ORDER BY kunjungan DESC LIMIT 5
        """)
        top_users = [{"nama": r[0], "kunjungan": r[1]} for r in cur.fetchall()]

        # 5. Waktu & Tren (Jam Sibuk Transaksi - Mocked from timestamps if exists)
        cur.execute("""
            SELECT EXTRACT(HOUR FROM date) as jam, COUNT(*) as jumlah
            FROM sales GROUP BY jam ORDER BY jumlah DESC LIMIT 5
        """)
        # Fallback if no timestamps variation
        jam_sibuk = [{"jam": f"{int(r[0])}:00", "transaksi": r[1]} for r in cur.fetchall()]
        
        data = {
            "stok": {
                "hampir_habis": hampir_habis,
                "overstock": overstock,
                "movements": movements,
                "tertinggi": stok_tertinggi,
                "terendah": stok_terendah,
                "total_jenis_obat": len(all_stock),
            },
            "penjualan": {"top_selling": top_selling, "jarang_dipakai": jarang_dipakai},
            "transaksi": transactions,
            "user": top_users,
            "waktu": jam_sibuk
        }
        return {"status": "success", "data": data}

def calculate_stock_status(pg_conn, nama_obat: str = None) -> dict:
    with pg_conn.cursor() as cur:
        q = """
            SELECT b.nama_obat as name, sum(b.stock_qty) as total_stock 
            FROM inventory_batches b 
        """
        if nama_obat:
            q += f" WHERE b.nama_obat ILIKE '%{nama_obat}%'"
        q += " GROUP BY b.nama_obat"
        
        cur.execute(q)
        rows = cur.fetchall()
        
        result = []
        for r in rows:
            stat = "Aman" if r[1] > 50 else "Kritis"
            result.append(f"{r[0]}: {r[1]} (Status: {stat})")
        return {"status": "success", "context": "\n".join(result) if result else "Tidak ada data stok."}

def detect_low_stock(pg_conn) -> dict:
    with pg_conn.cursor() as cur:
        q = """
            SELECT b.nama_obat as name, sum(b.stock_qty), l.name 
            FROM inventory_batches b 
            JOIN locations l ON b.location_id = l.id
            GROUP BY b.nama_obat, l.name
            HAVING sum(b.stock_qty) <= 50
        """
        cur.execute(q)
        rows = cur.fetchall()
        result = [f"Stok kritis di {r[2]}: {r[0]} sisa {r[1]}" for r in rows]
        return {"status": "success", "context": "\n".join(result) if result else "Stok aman semua."}

def detect_near_expiry(pg_conn, near_days=30) -> dict:
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT b.nama_obat as name, b.batch_no, b.expiry_date 
            FROM inventory_batches b 
            WHERE b.expiry_date <= CURRENT_DATE + INTERVAL '%s days'
        """, (near_days,))
        rows = cur.fetchall()
        res = [f"Batch {r[1]} obat {r[0]} kadaluarsa pada {r[2]}" for r in rows]
        return {"status": "success", "context": "\n".join(res) if res else "Tidak ada yang mendekati expired."}

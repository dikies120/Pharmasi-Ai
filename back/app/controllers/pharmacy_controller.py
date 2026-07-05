from typing import Dict, Any
from datetime import datetime, date, timedelta
import logging

from back.database.pgvektor import get_db_connection
from back.services.graph_data import GraphDataService

logger = logging.getLogger(__name__)


class PharmacyController:

    async def get_dashboard_data(self) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            medicines_data = GraphDataService.get_medicines_overview(conn)
            return {
                "timestamp": datetime.now().isoformat(),
                "medicines": medicines_data,
                "chat_trends": {"total_chats": 0},
            }
        finally:
            conn.close()

    async def get_inventory_realtime(self) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            # inventory_batches: id, medication_id, nama_obat, location_id, batch_no, expiry_date, stock_qty, unit
            # locations: id, name
            cursor.execute("""
                SELECT
                    ib.id,
                    ib.nama_obat,
                    COALESCE(ib.stock_qty, 0)  AS stok,
                    l.name                      AS lokasi,
                    ib.batch_no,
                    ib.expiry_date
                FROM inventory_batches ib
                LEFT JOIN locations l ON l.id = ib.location_id
                ORDER BY ib.stock_qty ASC NULLS LAST
            """)
            rows = cursor.fetchall()
            cursor.close()

            data = []
            for row in rows:
                data.append({
                    "id": str(row[0]),
                    "nama_obat": row[1] or "-",
                    "stok": int(row[2]) if row[2] is not None else 0,
                    "lokasi": row[3] or "Gudang Utama",
                    "batch_no": row[4] or "-",
                    "tanggal_kadaluarsa": str(row[5]) if row[5] else "-",
                })

            return {"timestamp": datetime.now().isoformat(), "data": data}
        except Exception as e:
            logger.error(f"Error get_inventory_realtime: {e}")
            raise ValueError(str(e))
        finally:
            conn.close()

    async def get_medicines_list(self) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            # medications: id, name, category, form
            # inventory_batches: nama_obat, stock_qty, expiry_date
            cursor.execute("""
                SELECT
                    m.name                          AS nama_obat,
                    COALESCE(SUM(ib.stock_qty), 0)  AS stok,
                    MIN(ib.expiry_date)              AS tanggal_kadaluarsa
                FROM medications m
                LEFT JOIN inventory_batches ib ON ib.medication_id = m.id
                GROUP BY m.name
                ORDER BY m.name ASC
            """)
            rows = cursor.fetchall()
            cursor.close()

            medicines = [
                {
                    "nama_obat": row[0],
                    "stok": int(row[1]) if row[1] else 0,
                    "tanggal_kadaluarsa": str(row[2]) if row[2] else "-",
                }
                for row in rows
            ]
            return {"timestamp": datetime.now().isoformat(), "medicines": medicines}
        except Exception as e:
            logger.error(f"Error get_medicines_list: {e}")
            raise ValueError(str(e))
        finally:
            conn.close()

    async def get_validation_queue(self) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            # Ambil semua resep beserta data pasien
            cursor.execute("""
                SELECT 
                    pr.id,
                    p.name,
                    p.date_of_birth,
                    p.medical_record_number,
                    NULL as poli,
                    p.allergies,
                    pr.diagnosis_notes,
                    pr.date
                FROM prescriptions pr
                JOIN patients p ON p.id = pr.patient_id
                ORDER BY pr.date DESC
            """)
            prescriptions_rows = cursor.fetchall()

            queue = []
            for row in prescriptions_rows:
                presc_id = row[0]
                # Hitung umur
                dob = row[2]
                age_str = "-"
                if dob:
                    today = date.today()
                    # Menangani kasus tanggal kabisat
                    try:
                        bday = dob.replace(year=today.year)
                    except ValueError:
                        bday = dob.replace(year=today.year, month=dob.month+1, day=1)
                    years = today.year - dob.year - (1 if today < bday else 0)
                    age_str = f"{years} Tahun"

                # Ambil daftar obat untuk resep ini
                cursor.execute("""
                    SELECT nama_obat, qty, instructions
                    FROM prescription_items
                    WHERE prescription_id = %s
                """, (presc_id,))
                items = cursor.fetchall()
                medicines_list = [f"{i[0]} ({i[1]}x) - {i[2]}" for i in items]

                queue.append({
                    "id": str(row[3]) if row[3] else f"RX-{presc_id}",
                    "name": str(row[1]),
                    "age": age_str,
                    "dateOfBirth": str(dob) if dob else "-",
                    "poli": str(row[4]) if row[4] else "Poli Umum",
                    "allergies": str(row[5]) if row[5] else "Tidak ada alergi yang diketahui",
                    "diagnosis": str(row[6]) if row[6] else "-",
                    "status": "VALIDASI",
                    "medicines": medicines_list
                })

            cursor.close()
            return {"timestamp": datetime.now().isoformat(), "queue": queue}
        except Exception as e:
            logger.error(f"Error get_validation_queue: {e}")
            raise ValueError(str(e))
        finally:
            conn.close()

    async def add_inventory_batch(self, data: Dict[str, Any]) -> Dict[str, Any]:
        nama_obat = data.get("nama_obat")
        batch_no = data.get("batch_no")
        expiry_date = data.get("expiry_date")
        stock_qty = int(data.get("stock_qty", 0)) if data.get("stock_qty") else 0
        unit = data.get("unit", "Box")
        location_id = data.get("location_id", 1)  # Default Gudang Utama
        
        if not all([nama_obat, batch_no, expiry_date, stock_qty > 0]):
            raise ValueError("Data tidak lengkap (nama_obat, batch_no, expiry_date, stock_qty wajib diisi)")

        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            
            # Cek apakah obat sudah ada di medications
            cursor.execute("SELECT id, name FROM medications WHERE lower(name) = lower(%s)", (nama_obat,))
            med_row = cursor.fetchone()
            
            if med_row:
                medication_id = med_row[0]
                # Gunakan nama obat asli dari master untuk konsistensi (huruf besar/kecil)
                nama_obat_master = med_row[1] 
            else:
                # Insert obat baru ke medications
                cursor.execute(
                    "INSERT INTO medications (name, category, form, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) RETURNING id",
                    (nama_obat, "Umum", unit)
                )
                medication_id = cursor.fetchone()[0]
                nama_obat_master = nama_obat

            # Cek apakah batch sudah ada di lokasi yang sama untuk update (opsional, tapi lebih aman INSERT saja sebagai restock)
            # Insert ke inventory_batches
            cursor.execute(
                """
                INSERT INTO inventory_batches 
                (medication_id, nama_obat, location_id, batch_no, expiry_date, stock_qty, unit, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                (medication_id, nama_obat_master, location_id, batch_no, expiry_date, stock_qty, unit)
            )
            batch_id = cursor.fetchone()[0]

            # Insert ke stock_movements (Mutasi masuk)
            cursor.execute(
                """
                INSERT INTO stock_movements
                (nama_obat, location_id, batch_id, type, qty, reference, date)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (nama_obat_master, location_id, batch_id, "IN", stock_qty, "RESTOCK MANUAL")
            )

            conn.commit()
            cursor.close()
            return {"status": "success", "message": f"Stok {nama_obat_master} berhasil ditambahkan", "batch_id": batch_id}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error add_inventory_batch: {e}")
            raise ValueError(f"Gagal menambahkan stok: {str(e)}")
        finally:
            conn.close()

    async def update_inventory_batch(self, batch_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        batch_no = data.get("batch_no")
        expiry_date = data.get("expiry_date")
        stock_qty = int(data.get("stock_qty", 0)) if data.get("stock_qty") else 0
        unit = data.get("unit")
        
        if not all([batch_no, expiry_date, stock_qty > 0, unit]):
            raise ValueError("Data tidak lengkap untuk update")

        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            
            # Cek apakah batch ada
            cursor.execute("SELECT nama_obat, location_id FROM inventory_batches WHERE id = %s", (batch_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Batch tidak ditemukan")
                
            nama_obat = row[0]
            location_id = row[1]

            # Update inventory_batches
            cursor.execute(
                """
                UPDATE inventory_batches 
                SET batch_no = %s, expiry_date = %s, stock_qty = %s, unit = %s
                WHERE id = %s
                """,
                (batch_no, expiry_date, stock_qty, unit, batch_id)
            )

            # Insert ke stock_movements sebagai log edit
            cursor.execute(
                """
                INSERT INTO stock_movements
                (nama_obat, location_id, batch_id, type, qty, reference, date)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                (nama_obat, location_id, batch_id, "IN", stock_qty, "EDIT BATCH MANUAL")
            )

            conn.commit()
            cursor.close()
            return {"status": "success", "message": f"Batch obat {nama_obat} berhasil diupdate"}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error update_inventory_batch: {e}")
            raise ValueError(f"Gagal update stok: {str(e)}")
        finally:
            conn.close()

    async def delete_inventory_batch(self, batch_id: int) -> Dict[str, Any]:
        conn = get_db_connection()
        if not conn:
            raise ValueError("Database tidak dapat diakses")
        try:
            cursor = conn.cursor()
            
            # Cek batch
            cursor.execute("SELECT nama_obat FROM inventory_batches WHERE id = %s", (batch_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Batch tidak ditemukan")
                
            nama_obat = row[0]

            cursor.execute("DELETE FROM inventory_batches WHERE id = %s", (batch_id,))

            conn.commit()
            cursor.close()
            return {"status": "success", "message": f"Batch obat {nama_obat} berhasil dihapus"}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error delete_inventory_batch: {e}")
            raise ValueError(f"Gagal menghapus stok: {str(e)}")
        finally:
            conn.close()



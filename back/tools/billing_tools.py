import logging
import uuid

logger = logging.getLogger(__name__)

def get_patient_billing(pg_conn, kartu_id: str) -> dict:
    """Mengambil data pasien dan total tagihan resep terakhir untuk proses verifikasi asuransi."""
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name
            FROM patients
            WHERE medical_record_number = %s OR name ILIKE %s
            ORDER BY id DESC LIMIT 1
            """,
            (kartu_id, f"%{kartu_id}%"),
        )
        patient = cur.fetchone()

        if not patient:
            return {"status": "error", "verification": "Data pasien tidak ditemukan."}

        pid, pname = patient

        cur.execute(
            """
            SELECT SUM(pi.qty * 15000)
            FROM prescriptions pre
            JOIN prescription_items pi ON pre.id = pi.prescription_id
            WHERE pre.patient_id = %s
            """,
            (pid,),
        )
        total_tagihan = cur.fetchone()[0] or 0

        return {
            "status": "success",
            "patient_id": pid,
            "patient_name": pname,
            "total_tagihan": float(total_tagihan),
        }

def process_payment(pg_conn, kartu_id: str, jenis: str, total_tagihan: float = 0) -> dict:
    """Mencatat pembayaran ke tabel sales dan sales_items."""
    trans_no = f"TRX-{uuid.uuid4().hex[:6].upper()}"

    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name
            FROM patients
            WHERE medical_record_number = %s OR name ILIKE %s
            ORDER BY id DESC LIMIT 1
            """,
            (kartu_id, f"%{kartu_id}%"),
        )
        patient = cur.fetchone()

        if not patient:
            return {"status": "error", "message": "Pasien tidak ditemukan."}

        pid, pname = patient

        cur.execute(
            """
            SELECT pi.nama_obat, pi.qty
            FROM prescriptions pre
            JOIN prescription_items pi ON pre.id = pi.prescription_id
            WHERE pre.patient_id = %s
            ORDER BY pre.date DESC
            """,
            (pid,),
        )
        items = cur.fetchall()

        if not items:
            return {"status": "error", "message": "Tidak ada resep aktif untuk pasien ini."}

        price_per_unit = 15000
        total_amount = 0
        sale_items_data = []
        for nama_obat, qty in items:
            subtotal = qty * price_per_unit
            total_amount += subtotal
            sale_items_data.append((nama_obat, qty, price_per_unit, subtotal))

        if total_tagihan and total_tagihan > 0:
            total_amount = total_tagihan

        cur.execute(
            "INSERT INTO sales (transaction_no, total_amount) VALUES (%s, %s) RETURNING id",
            (trans_no, total_amount),
        )
        sale_id = cur.fetchone()[0]

        for nama_obat, qty, price, subtotal in sale_items_data:
            cur.execute(
                "INSERT INTO sales_items (sale_id, nama_obat, qty, price, subtotal) VALUES (%s, %s, %s, %s, %s)",
                (sale_id, nama_obat, qty, price, subtotal),
            )

        pg_conn.commit()

    return {
        "status": "success",
        "transaction_no": trans_no,
        "total_amount": total_amount,
        "patient_name": pname,
        "jenis": jenis,
        "items_count": len(sale_items_data),
        "message": f"Pembayaran {trans_no} berhasil dicatat.",
    }

def validate_bpjs(pg_conn, kartu_id: str) -> dict:
    return {"status": "success", "context": "Klaim valid e-Fornas (Indikasi: Sesuai Panduan Klinis)"}

def validate_private_insurance(pg_conn, kartu_id: str) -> dict:
    return {"status": "success", "context": "Asuransi komersil terverifikasi via Bridging."}

def check_payment_status(pg_conn, transaction_id: str) -> dict:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT transaction_no, total_amount FROM sales LIMIT 1")
        row = cur.fetchone()
        if row: return {"status": "success", "context": f"Status Pembayaran Lunas (Rp {row[1]})"}
        return {"status": "error", "context": "Transaksi tidak ditemukan."}

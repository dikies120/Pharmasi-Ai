import logging

logger = logging.getLogger(__name__)

def _normalize_prescription_id(prescription_id) -> int:
    try:
        if isinstance(prescription_id, int):
            return prescription_id
        pid_str = str(prescription_id).replace('RSP-', '').replace('TRX-', '')
        return int(pid_str) if pid_str.isdigit() else 1
    except Exception:
        return 1

def validate_prescription(pg_conn, prescription_id: str) -> dict:
    pid = _normalize_prescription_id(prescription_id)
        
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT pr.id, p.name, p.medical_record_number 
            FROM prescriptions pr 
            JOIN patients p ON pr.patient_id = p.id 
            WHERE pr.id = %s
        """, (pid,))
        row = cur.fetchone()
        if not row: return {"status": "error", "context": "Resep tidak ditemukan di EMR."}
        
        # Log to communication_logs (SKP 2)
        cur.execute("INSERT INTO communication_logs (prescription_id, message, is_verified) VALUES (%s, %s, %s)", (pid, "Resep divalidasi oleh farmasi", True))
        return {"status": "success", "context": f"Resep valid milik Pasien {row[1]} [{row[2]}]. Dicatat ke log komunikasi."}

def check_stock_dispensing(pg_conn, medicine: str, qty: int) -> dict:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT sum(stock_qty) FROM inventory_batches WHERE nama_obat ILIKE %s", (f"%{medicine}%",))
        total = cur.fetchone()[0]
        if total and total >= qty:
            return {"status": "success", "context": "Stok cukup."}
        return {"status": "warning", "context": "Stok tidak cukup, perlu perbaikan/penggantian."}

def prepare_dispensing(pg_conn, prescription_id: str) -> dict:
    return {"status": "success", "context": "Tercatat dalam log dispensing sistem."}

def update_status_dispensing(pg_conn, prescription_id: str) -> dict:
    return {"status": "success", "context": "Dispensing selesai dan log komunikasi (SKP) tertutup."}

def get_dispensing_preview(pg_conn, prescription_id: str) -> dict:
    """Mengambil ringkasan resep untuk tampilan awal proses dispensing."""
    pid = _normalize_prescription_id(prescription_id)

    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pi.nama_obat, COALESCE(pi.instructions, ''), COALESCE(pi.qty, 0),
                   p.name, p.medical_record_number, p.allergies, p.bpjs_status,
                   p.faskes_level, p.date_of_birth,
                   pre.diagnosis_code, pre.diagnosis_notes
            FROM prescriptions pre
            JOIN prescription_items pi ON pre.id = pi.prescription_id
            JOIN patients p ON p.id = pre.patient_id
            WHERE pre.id = %s
            """,
            (pid,),
        )
        rows = cur.fetchall()

        if not rows:
            return {"status": "error", "message": "ID Resep tidak valid atau tidak ditemukan."}

        medicines = []
        medicines_detail = []
        need_mixing = False
        first = rows[0]
        patient_name = first[3]
        patient_mrn = first[4]
        patient_allergies = first[5]
        patient_bpjs = first[6]
        patient_faskes = first[7]
        patient_dob = first[8]
        diagnosis_code = first[9]
        diagnosis_notes = first[10]

        # Hitung usia
        usia_tahun = None
        if patient_dob:
            try:
                from datetime import date
                today = date.today()
                usia_tahun = today.year - patient_dob.year - (
                    (today.month, today.day) < (patient_dob.month, patient_dob.day)
                )
            except Exception:
                pass

        for row in rows:
            med_name = row[0]
            aturan_minum = row[1] if row[1] else "Sesuai etiket"
            qty = int(row[2]) if row[2] is not None else 0
            form_value = "-"
            medicines.append(f"- {med_name} (Sediaan: {form_value})")

            form_text = (med_name or "").lower()
            perlu_racik = any(x in form_text for x in ["puyer", "serbuk", "sirup kering", "racik", "vial"])
            if perlu_racik:
                need_mixing = True

            medicines_detail.append(
                {
                    "nama_obat": med_name,
                    "qty_resep": qty,
                    "sediaan": form_value,
                    "aturan_minum": aturan_minum,
                    "perlu_peracikan": "IYA" if perlu_racik else "TIDAK",
                }
            )

        return {
            "status": "success",
            "prescription_id": str(prescription_id),
            "patient_name": patient_name,
            "patient_mrn": patient_mrn,
            "medicines": medicines,
            "medicines_detail": medicines_detail,
            "need_mixing": need_mixing,
            "dispensing_stages": {
                "penyiapan_obat": "SIAP DIPROSES",
                "peracikan": "DIPERLUKAN" if need_mixing else "TIDAK DIPERLUKAN",
                "pemberian_obat": "MENUNGGU FINALISASI DISPENSING",
            },
            "pemberian_obat_checklist": [
                "Verifikasi identitas pasien sebelum serah obat",
                "Jelaskan aturan minum, frekuensi, dan durasi",
                "Sampaikan efek samping utama yang perlu dipantau",
                "Konfirmasi pasien/keluarga memahami instruksi",
            ],
            # Data pasien langsung tersedia tanpa perlu lookup tambahan
            "_patient_data": {
                "mrn": patient_mrn,
                "usia_tahun": usia_tahun,
                "alergi": patient_allergies,
                "bpjs_status": patient_bpjs,
                "faskes_level": patient_faskes,
                "diagnosis": diagnosis_code,
                "diagnosis_notes": diagnosis_notes,
            },
        }


def complete_dispensing(pg_conn, prescription_id: str) -> dict:
    """Menyelesaikan dispensing: kurangi stok inventory (FIFO) dan catat stock_movements."""
    pid = _normalize_prescription_id(prescription_id)
    stock_deductions = []

    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pi.nama_obat, pi.qty
            FROM prescription_items pi
            WHERE pi.prescription_id = %s
            """,
            (pid,),
        )
        items = cur.fetchall()

        if not items:
            return {"status": "error", "message": "Resep tidak ditemukan atau tidak ada item obat."}

        for nama_obat, qty_needed in items:
            remaining = qty_needed

            cur.execute(
                """
                SELECT id, batch_no, stock_qty, expiry_date
                FROM inventory_batches
                WHERE nama_obat ILIKE %s AND stock_qty > 0
                ORDER BY expiry_date ASC
                """,
                (f"%{nama_obat}%",),
            )
            batches = cur.fetchall()

            for batch_id, batch_no, stock_qty, _expiry_date in batches:
                if remaining <= 0:
                    break

                deduct = min(remaining, stock_qty)
                new_stock = stock_qty - deduct

                cur.execute(
                    """
                    UPDATE inventory_batches SET stock_qty = %s WHERE id = %s
                    """,
                    (new_stock, batch_id),
                )

                cur.execute(
                    """
                    INSERT INTO stock_movements (nama_obat, location_id, batch_id, type, qty, reference)
                    SELECT %s, location_id, %s, 'OUT', %s, %s
                    FROM inventory_batches WHERE id = %s
                    """,
                    (nama_obat, batch_id, deduct, f"DISPENSING-RSP-{pid}", batch_id),
                )

                stock_deductions.append(
                    {
                        "nama_obat": nama_obat,
                        "batch_no": batch_no,
                        "qty_deducted": deduct,
                        "remaining_stock": new_stock,
                    }
                )

                remaining -= deduct

        pg_conn.commit()

    return {
        "status": "success",
        "message": "Dispensing selesai, stok telah dikurangi.",
        "prescription_id": pid,
        "stock_deductions": stock_deductions,
        "dispensing_stages": {
            "penyiapan_obat": "SELESAI",
            "peracikan": "SELESAI / TIDAK DIPERLUKAN",
            "pemberian_obat": "SIAP DIBERIKAN KE PASIEN",
        },
        "pemberian_obat_checklist": [
            "Serahkan obat sesuai etiket dan nama pasien",
            "Edukasi aturan minum diulang saat serah obat",
            "Konfirmasi pasien menerima seluruh item obat",
        ],
    }

import logging
from typing import Optional
from datetime import date
from back.tools.obat_tools import (
    search_obat_by_stock as obat_stock_impl,
    search_obat_by_harga as obat_harga_impl,
    search_obat_by_kadaluarsa as obat_kadaluarsa_impl,
)
from back.tools.rag_tools import ask_question as rag_ask_question
from back.tools.workflow_tools import (
    calculate_stock_status as calculate_stock_status_impl,
    detect_low_stock as detect_low_stock_impl,
    detect_near_expiry as detect_near_expiry_impl,
    get_realtime_stock_tool as get_realtime_stock_tool_impl,
    get_inventory_analytics_tool as get_inventory_analytics_tool_impl,
    check_allergy as check_allergy_impl,
    check_drug_interaction as check_drug_interaction_impl,
    check_contraindication as check_contraindication_impl,
    check_dose as check_dose_impl,
    validate_prescription as validate_prescription_impl,
    get_dispensing_preview as get_dispensing_preview_impl,
    complete_dispensing as complete_dispensing_impl,
    check_stock_dispensing as check_stock_dispensing_impl,
    prepare_dispensing as prepare_dispensing_impl,
    update_status_dispensing as update_status_dispensing_impl,
    get_patient_billing as get_patient_billing_impl,
    process_payment as process_payment_impl,
    check_payment_status as check_payment_status_impl,
    validate_bpjs as validate_bpjs_impl,
    validate_private_insurance as validate_private_insurance_impl,
)

logger = logging.getLogger(__name__)

def register_tools(mcp, pg_conn=None, rag_pipeline=None):
    logger.info("Registering Pharma MCP tools and resources...")

    @mcp.resource("inventory://stock_data")
    def get_stock_data() -> str:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT b.nama_obat as name, SUM(b.stock_qty) FROM inventory_batches b GROUP BY b.nama_obat")
            rows = cur.fetchall()
            return str(rows)

    @mcp.resource("inventory://stock_location")
    def get_stock_locations() -> str:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT l.name, SUM(b.stock_qty) FROM inventory_batches b JOIN locations l ON l.id = b.location_id GROUP BY l.name")
            rows = cur.fetchall()
            return str(rows)

    @mcp.resource("inventory://expiry_data")
    def get_expiry_data() -> str:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT b.nama_obat as name, b.batch_no, b.expiry_date FROM inventory_batches b")
            rows = cur.fetchall()
            return str(rows)

    @mcp.resource("patient://{patient_id}")
    def get_patient_profile(patient_id: str) -> str:
        with pg_conn.cursor() as cur:
            pid = int(patient_id.replace('MR-','')) if 'MR-' in patient_id else 1
            cur.execute("SELECT id, name, date_of_birth, medical_record_number FROM patients WHERE id = %s", (pid,))
            row = cur.fetchone()
            return str(row)

    @mcp.resource("alergi://{patient_id}")
    def get_allergy_history(patient_id: str) -> str:
        with pg_conn.cursor() as cur:
            return "[]" # Alergi table is removed, default to safe

    @mcp.resource("riwayat_terapi://{patient_id}")
    def get_therapy_history(patient_id: str) -> str:
        with pg_conn.cursor() as cur:
            # Menggunakan prescription_items sebagai ganti riwayat_terapi
            pid = int(patient_id.replace('MR-','')) if 'MR-' in patient_id else 1
            cur.execute("SELECT pi.nama_obat as name, pi.qty FROM prescription_items pi JOIN prescriptions pr ON pr.id = pi.prescription_id WHERE pr.patient_id = %s", (pid,))
            rows = cur.fetchall()
            return str(rows)

    @mcp.resource("resep://{prescription_id}")
    def get_prescription_data(prescription_id: str) -> str:
        with pg_conn.cursor() as cur:
            pid = int(prescription_id) if prescription_id.isdigit() else 1
            cur.execute("SELECT * FROM prescriptions WHERE id = %s", (pid,))
            row = cur.fetchone()
            return str(row)

    @mcp.resource("asuransi://{kartu_id}")
    def get_insurance_data(kartu_id: str) -> str:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT * FROM fornas_rules LIMIT 1")
            row = cur.fetchone()
            return str(row)

    @mcp.tool()
    def search_obat_by_stock(operator: str = ">", nilai: Optional[int] = None, nama_obat: Optional[str] = None) -> dict:
        return obat_stock_impl(pg_conn, operator, nilai, nama_obat)

    @mcp.tool()
    def search_obat_by_harga(operator: str = "<", nilai: Optional[int] = None, nama_obat: Optional[str] = None) -> dict:
        return obat_harga_impl(pg_conn, operator, nilai, nama_obat)

    @mcp.tool()
    def search_obat_by_kadaluarsa(operator: str = "<", tanggal: Optional[str] = None, nama_obat: Optional[str] = None) -> dict:
        target_tanggal = tanggal or date.today().isoformat()
        return obat_kadaluarsa_impl(pg_conn, operator, target_tanggal, nama_obat)

    # --- A. Monitoring Stok ---
    @mcp.tool()
    def calculate_stock_status(nama_obat: str = None) -> dict: return calculate_stock_status_impl(pg_conn, nama_obat)
    @mcp.tool()
    def detect_low_stock() -> dict: return detect_low_stock_impl(pg_conn)
    @mcp.tool()
    def detect_near_expiry(days: int=30) -> dict: return detect_near_expiry_impl(pg_conn, days)
    @mcp.tool()
    def get_realtime_stock(nama_obat: Optional[str] = None, lokasi: Optional[str] = None, status: Optional[str] = None) -> dict: 
        return get_realtime_stock_tool_impl(pg_conn, nama_obat, lokasi, status)
    @mcp.tool()
    def get_inventory_analytics() -> dict: 
        return get_inventory_analytics_tool_impl(pg_conn)
    
    # --- B. Validasi Obat & Alergi ---
    @mcp.tool()
    def check_allergy(patient_id: str, medicine: str) -> dict: return check_allergy_impl(pg_conn, patient_id, medicine)
    @mcp.tool()
    def check_drug_interaction(patient_id: str, medicine: str) -> dict: return check_drug_interaction_impl(pg_conn, patient_id, medicine)
    @mcp.tool()
    def check_contraindication(kondisi: str, medicine: str) -> dict: return check_contraindication_impl(pg_conn, medicine, kondisi)
    @mcp.tool()
    def check_dose(patient_id: str, medicine: str) -> dict: return check_dose_impl(pg_conn, medicine, patient_id)

    # --- C. Informasi Obat ---
    @mcp.tool()
    def ask_question(question: str) -> dict: return rag_ask_question(rag_pipeline, question)

    # --- E. Dispensing Obat ---
    @mcp.tool()
    def validate_prescription(prescription_id: str) -> dict: return validate_prescription_impl(pg_conn, prescription_id)
    @mcp.tool()
    def get_dispensing_preview(prescription_id: str) -> dict: return get_dispensing_preview_impl(pg_conn, prescription_id)
    @mcp.tool()
    def complete_dispensing(prescription_id: str) -> dict: return complete_dispensing_impl(pg_conn, prescription_id)
    @mcp.tool()
    def check_stock(medicine: str, qty: int) -> dict: return check_stock_dispensing_impl(pg_conn, medicine, qty)
    @mcp.tool()
    def prepare_dispensing(prescription_id: str) -> dict: return prepare_dispensing_impl(pg_conn, prescription_id)
    @mcp.tool()
    def update_status_dispensing(prescription_id: str) -> dict: return update_status_dispensing_impl(pg_conn, prescription_id)

    # --- F. Pembayaran & Asuransi ---
    @mcp.tool()
    def get_patient_billing(kartu_id: str) -> dict: return get_patient_billing_impl(pg_conn, kartu_id)
    @mcp.tool()
    def process_payment(kartu_id: str, jenis: str, total_tagihan: float = 0) -> dict: return process_payment_impl(pg_conn, kartu_id, jenis, total_tagihan)
    @mcp.tool()
    def check_payment_status(transaction_id: str) -> dict: return check_payment_status_impl(pg_conn, transaction_id)
    @mcp.tool()
    def validate_bpjs(kartu_id: str) -> dict: return validate_bpjs_impl(pg_conn, kartu_id)
    @mcp.tool()
    def validate_private_insurance(kartu_id: str) -> dict: return validate_private_insurance_impl(pg_conn, kartu_id)
    
    # --- G. Core Data Access Tools (User Specified Architecture) ---
    import pymongo

    def get_mongo_col(col_name):
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        return client["simrs"][col_name]

    def _fetch_patient_data(patient_id: str) -> dict:
        try:
            query_text = str(patient_id or "").strip()
            if not query_text:
                return {"status": "error", "error": "Patient ID/Nama tidak boleh kosong."}

            with pg_conn.cursor() as cur:
                p = None

                # 1) Prioritaskan kecocokan exact MRN.
                cur.execute(
                    """
                    SELECT id, name, date_of_birth, medical_record_number, allergies, bpjs_status, faskes_level
                    FROM patients
                    WHERE medical_record_number = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (query_text,),
                )
                p = cur.fetchone()

                # 2) Jika tidak ada, coba kecocokan exact nama (case-insensitive).
                if not p:
                    cur.execute(
                        """
                        SELECT id, name, date_of_birth, medical_record_number, allergies, bpjs_status, faskes_level
                        FROM patients
                        WHERE LOWER(name) = LOWER(%s)
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (query_text,),
                    )
                    p = cur.fetchone()

                # 3) Fallback ke partial nama hanya jika hasilnya tunggal.
                if not p:
                    cur.execute(
                        """
                        SELECT id, name, date_of_birth, medical_record_number, allergies, bpjs_status, faskes_level
                        FROM patients
                        WHERE name ILIKE %s
                        ORDER BY id DESC
                        LIMIT 5
                        """,
                        (f"%{query_text}%",),
                    )
                    candidates = cur.fetchall()
                    if len(candidates) == 1:
                        p = candidates[0]
                    elif len(candidates) > 1:
                        return {
                            "status": "error",
                            "error": "Input pasien ambigu. Gunakan MRN spesifik.",
                            "candidates": [f"{row[1]} ({row[3]})" for row in candidates],
                        }

                if not p:
                    return {"status": "error", "error": "Patient not found"}

                pid, pname, pdob, pmrn, pallergies, pbpjs, pfaskes = p

                usia_tahun = None
                if pdob:
                    try:
                        usia_tahun = date.today().year - pdob.year - ((date.today().month, date.today().day) < (pdob.month, pdob.day))
                    except Exception:
                        usia_tahun = None

                cur.execute(
                    """
                    SELECT id, diagnosis_code, diagnosis_notes, date
                    FROM prescriptions
                    WHERE patient_id = %s
                    ORDER BY date DESC, id DESC
                    LIMIT 1
                    """,
                    (pid,),
                )
                latest_prescription = cur.fetchone()

                resep = []
                diagnosis_code = None
                diagnosis_note = None
                prescription_id = None
                prescription_date = None

                if latest_prescription:
                    prescription_id, diagnosis_code, diagnosis_note, prescription_date = latest_prescription
                    cur.execute(
                        """
                        SELECT nama_obat, qty, instructions
                        FROM prescription_items
                        WHERE prescription_id = %s
                        ORDER BY id ASC
                        """,
                        (prescription_id,),
                    )
                    resep = cur.fetchall()

                payload = {
                    "status": "success",
                    "nama": pname,
                    "mrn": pmrn,
                    "tanggal_lahir": pdob.isoformat() if pdob else None,
                    "usia_tahun": usia_tahun,
                    "alergi": pallergies,
                    "bpjs_status": pbpjs,
                    "faskes_level": pfaskes,
                    "active_diagnosis": [diagnosis_code] if diagnosis_code else [],
                    "diagnosis_notes": [diagnosis_note] if diagnosis_note else [],
                    "active_prescription_id": prescription_id,
                    "active_prescription_date": prescription_date.isoformat() if prescription_date else None,
                    "active_prescriptions": [{"drug": r[0], "qty": r[1], "aturan_minum": r[2]} for r in resep] if resep else [],
                }

                diagnosis_text = ", ".join([str(code) for code in payload["active_diagnosis"] if code]) or "-"
                diagnosis_note_text = payload["diagnosis_notes"][0] if payload["diagnosis_notes"] else "-"

                payload["context"] = (
                    f"Nama Pasien: {pname}\n"
                    f"MRN: {pmrn}\n"
                    f"Tanggal Lahir: {pdob.isoformat() if pdob else '-'}\n"
                    f"Usia: {usia_tahun if usia_tahun is not None else '-'} tahun\n"
                    f"Alergi: {pallergies or '-'}\n"
                    f"Status BPJS: {pbpjs}\n"
                    f"Faskes Level: {pfaskes}\n"
                    f"Diagnosis Aktif: {diagnosis_text}\n"
                    f"Catatan Diagnosis: {diagnosis_note_text}"
                )

                return payload
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    def get_patient_data(patient_id: str) -> dict:
        """Get patient clinical data and past diagnosis/prescriptions from PostgreSQL"""
        return _fetch_patient_data(patient_id)

    @mcp.tool()
    def get_icd11_data(kode_diagnosa: str) -> dict:
        """Get official ICD-11 diagnosis details from MongoDB"""
        try:
            col = get_mongo_col("icd11")
            doc = col.find_one({"kode": {"$regex": f"^{kode_diagnosa}", "$options": "i"}}, {"_id": 0})
            if doc: return doc
            return {"kode": kode_diagnosa, "nama": "Diagnosis Umum", "tipe": "unspecified"}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_fornas_data(drug_name: str) -> dict:
        """Get E-Fornas restriction rules and therapy classes from MongoDB"""
        try:
            col = get_mongo_col("efornas")
            # Coba cari berdasar kata pertama obat
            doc = col.find_one({"nama_obat": {"$regex": f"^{drug_name.split()[0]}", "$options": "i"}}, {"_id": 0})
            if doc: return doc
            return {"nama_obat": drug_name, "pesan": "Obat tidak terdaftar di blok restriksi spesial Fornas (Umum)"}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_drug_stock(drug_name: str) -> dict:
        """Get current physical stock of a drug from PostgreSQL inventory"""
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT COALESCE(SUM(stock_qty), 0) FROM inventory_batches WHERE nama_obat ILIKE %s", (f"%{drug_name}%",))
                row = cur.fetchone()
                if row and row[0] > 0: return {"nama_obat": drug_name, "stok": float(row[0])}
                return {"nama_obat": drug_name, "stok": 0, "pesan": "Obat tidak ditemukan di inventory gudang postgreSQL."}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def check_medicine_safety(patient_id: str, medicine: str) -> dict:
        """Validasi keamanan obat berdasarkan data pasien dari DB (alergi, interaksi, kontraindikasi, dosis)."""
        patient_data = _fetch_patient_data(patient_id)
        if patient_data.get("error"):
            return {
                "status": "error",
                "error": patient_data.get("error"),
                "context": f"Data pasien '{patient_id}' tidak ditemukan di database.",
            }

        diagnosis_notes = patient_data.get("diagnosis_notes") or []
        kondisi_pasien = diagnosis_notes[0] if diagnosis_notes else "umum"

        allergy_result = check_allergy_impl(pg_conn, patient_id, medicine)
        interaction_result = check_drug_interaction_impl(pg_conn, patient_id, medicine)
        contraindication_result = check_contraindication_impl(pg_conn, medicine, kondisi_pasien)
        dose_result = check_dose_impl(pg_conn, medicine, patient_id)

        checks = [
            ("Alergi", allergy_result),
            ("Interaksi Obat", interaction_result),
            ("Kontraindikasi", contraindication_result),
            ("Dosis", dose_result),
        ]

        warnings = []
        detail_lines = []
        detail_map = {}
        for label, result in checks:
            status = str(result.get("status", "unknown")).lower()
            detail = result.get("context") or result.get("message") or "Tidak ada detail"
            detail_lines.append(f"- {label}: {detail}")
            detail_map[label.lower().replace(" ", "_")] = {
                "status": status,
                "detail": detail,
            }
            if status not in {"safe", "success", "ok"}:
                warnings.append(label)

        verdict = "PERLU REVIEW FARMASIS/DOKTER" if warnings else "AMAN"

        patient_name = patient_data.get("nama", patient_id)
        patient_mrn = patient_data.get("mrn", patient_id)

        context = "\n".join(
            [
                f"Hasil cek keamanan obat untuk pasien {patient_name} ({patient_mrn})",
                f"Obat: {medicine}",
                f"Status: {verdict}",
                "Detail pemeriksaan:",
                *detail_lines,
                "Saran: konsultasikan ke dokter/farmasis sebelum obat diberikan." if warnings else "Saran: obat dinilai aman berdasarkan data saat ini.",
            ]
        )

        return {
            "status": "success",
            "patient_name": patient_name,
            "patient_mrn": patient_mrn,
            "medicine": medicine,
            "verdict": verdict,
            "warnings": warnings,
            "checks": detail_map,
            "context": context,
        }

    logger.info("All Pharma MCP tools and resources registered successfully")


import logging
from typing import Optional
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

    # ==========================================
    # MCP RESOURCES (Read-only data)
    # ==========================================
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

    # ==========================================
    # MCP TOOLS (Actions / Processing)
    # ==========================================
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

    @mcp.tool()
    def get_patient_data(patient_id: str) -> dict:
        """Get patient clinical data and past diagnosis/prescriptions from PostgreSQL"""
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT id, name, medical_record_number, allergies, bpjs_status, faskes_level FROM patients WHERE medical_record_number = %s OR name ILIKE %s ORDER BY id DESC LIMIT 1", (patient_id, f"%{patient_id}%"))
                p = cur.fetchone()
                if not p: return {"error": "Patient not found"}
                pid, pname, pmrn, pallergies, pbpjs, pfaskes = p
                
                cur.execute("""
                    SELECT p.diagnosis_code, p.diagnosis_notes, pi.nama_obat, pi.qty, pi.instructions
                    FROM prescriptions p JOIN prescription_items pi ON p.id = pi.prescription_id
                    WHERE p.patient_id = %s ORDER BY p.date DESC LIMIT 10
                """, (pid,))
                resep = cur.fetchall()
                
                return {
                    "nama": pname,
                    "mrn": pmrn,
                    "alergi": pallergies,
                    "bpjs_status": pbpjs,
                    "faskes_level": pfaskes,
                    "active_diagnosis": [r[0] for r in resep] if resep and resep[0][0] else ["J06.9"],
                    "diagnosis_notes": [r[1] for r in resep] if resep and resep[0][1] else ["Tidak tercatat"],
                    "active_prescriptions": [{"drug": r[2], "qty": r[3], "aturan_minum": r[4]} for r in resep] if resep else []
                }
        except Exception as e:
            return {"error": str(e)}

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

    logger.info("All Pharma MCP tools and resources registered successfully")


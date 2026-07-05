import pymongo
from datetime import date

from back.core.settings import settings

def get_mongo_col(col_name):
    client = pymongo.MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
    return client[settings.MONGO_DB][col_name]

def _fetch_patient_data(pg_conn, patient_id: str) -> dict:
    try:
        query_text = str(patient_id or "").strip()
        if not query_text:
            return {"status": "error", "error": "Patient ID/Nama tidak boleh kosong."}

        with pg_conn.cursor() as cur:
            p = None

            # 1) Prioritaskan kecocokan exact NIK.
            cur.execute(
                """
                SELECT id, name, date_of_birth, medical_record_number, allergies, bpjs_status, faskes_level
                FROM patients
                WHERE nik = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (query_text,),
            )
            p = cur.fetchone()

            # 2) Jika tidak ada, coba kecocokan exact MRN.
            if not p:
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

            resep_lines = []
            if payload["active_prescriptions"]:
                for r in payload["active_prescriptions"]:
                    resep_lines.append(f"- {r['drug']} (Qty: {r['qty']}) - Aturan: {r['aturan_minum']}")
            resep_text = "\n".join(resep_lines) if resep_lines else "Tidak ada obat/resep aktif."

            payload["context"] = (
                f"Nama Pasien: {pname}\n"
                f"MRN: {pmrn}\n"
                f"Tanggal Lahir: {pdob.isoformat() if pdob else '-'}\n"
                f"Usia: {usia_tahun if usia_tahun is not None else '-'} tahun\n"
                f"Alergi: {pallergies or '-'}\n"
                f"Status BPJS: {pbpjs}\n"
                f"Faskes Level: {pfaskes}\n"
                f"Diagnosis Aktif: {diagnosis_text}\n"
                f"Catatan Diagnosis: {diagnosis_note_text}\n"
                f"Obat/Resep Saat Ini:\n{resep_text}"
            )

            return payload
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_patient_data_impl(pg_conn, patient_id: str) -> dict:
    """Get patient clinical data and past diagnosis/prescriptions from PostgreSQL"""
    return _fetch_patient_data(pg_conn, patient_id)

def get_icd11_data_impl(kode_diagnosa: str) -> dict:
    """Get official ICD-11 diagnosis details from MongoDB"""
    try:
        col = get_mongo_col("icd11")
        doc = col.find_one({"kode": {"$regex": f"^{kode_diagnosa}", "$options": "i"}}, {"_id": 0})
        if doc: return doc
        return {"kode": kode_diagnosa, "nama": "Diagnosis Umum", "tipe": "unspecified"}
    except Exception as e:
        return {"error": str(e)}

def get_fornas_data_impl(drug_name: str) -> dict:
    """Get E-Fornas restriction rules and therapy classes from MongoDB"""
    try:
        col = get_mongo_col("efornas")
        doc = col.find_one({"nama_obat": {"$regex": f"^{drug_name.split()[0]}", "$options": "i"}}, {"_id": 0})
        if doc: return doc
        return {"nama_obat": drug_name, "pesan": "Obat tidak terdaftar di blok restriksi spesial Fornas (Umum)"}
    except Exception as e:
        return {"error": str(e)}

def get_drug_stock_impl(pg_conn, drug_name: str) -> dict:
    """Get current physical stock of a drug from PostgreSQL inventory"""
    try:
        with pg_conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(stock_qty), 0) FROM inventory_batches WHERE nama_obat ILIKE %s", (f"%{drug_name}%",))
            row = cur.fetchone()
            if row and row[0] > 0: return {"nama_obat": drug_name, "stok": float(row[0])}
            return {"nama_obat": drug_name, "stok": 0, "pesan": "Obat tidak ditemukan di inventory gudang postgreSQL."}
    except Exception as e:
        return {"error": str(e)}



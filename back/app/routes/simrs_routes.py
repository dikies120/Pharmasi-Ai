from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from back.database.pgvektor import get_db_connection

router = APIRouter(prefix="/simrs", tags=["SIM RS Data"])

@router.get("/{nik}")
async def get_simrs_data(nik: str) -> Dict[str, Any]:
    if not nik:
        raise HTTPException(status_code=400, detail="NIK tidak boleh kosong")
        
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Gagal koneksi ke database SIM RS")
        
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id, name, date_of_birth, medical_record_number FROM patients WHERE nik = %s", (nik,))
        patient = cur.fetchone()
        
        if not patient:
            raise HTTPException(status_code=404, detail=f"Data pasien dengan NIK {nik} tidak ditemukan di SIM RS")
            
        patient_id = patient[0]
        nama = patient[1]
        
        cur.execute("SELECT id, diagnosis_notes, date FROM prescriptions WHERE patient_id = %s ORDER BY date DESC LIMIT 1", (patient_id,))
        prescription = cur.fetchone()
        
        diagnosa = "Belum ada diagnosa"
        obat = []
        tanggal_kunjungan = ""
        
        if prescription:
            prescription_id = prescription[0]
            diagnosa = prescription[1]
            tanggal_kunjungan = prescription[2].strftime("%Y-%m-%d") if prescription[2] else ""
            
            cur.execute("SELECT nama_obat, qty, instructions FROM prescription_items WHERE prescription_id = %s", (prescription_id,))
            items = cur.fetchall()
            for item in items:
                obat.append({
                    "nama": item[0],
                    "dosis": f"Qty: {item[1]}",
                    "waktu": item[2]
                })
                
        cur.close()
        return {
            "nik": nik,
            "nama": nama,
            "diagnosa": diagnosa,
            "obat": obat,
            "tanggal_kunjungan": tanggal_kunjungan
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

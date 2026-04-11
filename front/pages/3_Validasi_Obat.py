import streamlit as st
import requests
from components.theme import apply_custom_theme

st.set_page_config(page_title="Validasi Obat", layout="wide")
apply_custom_theme()

st.title("Smart Drug Safety Checker (SKP)")
st.info("Sistem akan menganalisis resep pasien dengan database e-MR, mengecek stok, interaksi, dan alergi melalui AI Agent (MCP).")

pasien_id = st.text_input("ID / Nama Pasien", value="MR-001")

if st.button("Jalankan Validasi Resep", type="primary"):
    with st.spinner("Mengambil Data Pasien & Mengirim resep ke AI Agent..."):
        try:
            res = requests.post("http://localhost:8000/api/v1/validasi-obat/", json={
                "patient_id": pasien_id
            })
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "error":
                    st.error(data.get("message"))
                else:
                    # Simpan hasil validasi ke session_state untuk workflow
                    st.session_state["validasi_result"] = data
                    st.session_state["validasi_patient_id"] = pasien_id
                    st.session_state["validasi_done"] = True
            else:
                st.error("Gagal melakukan validasi. Periksa koneksi.")
        except Exception as e:
            st.error(str(e))

# Tampilkan hasil validasi jika sudah ada di session
if st.session_state.get("validasi_done") and st.session_state.get("validasi_result"):
    data = st.session_state["validasi_result"]
    
    st.write("---")
    
    st.subheader("Status Validasi (Tahap 1)")
    val = data.get("validasi", {})
    cols = st.columns(3)
    with cols[0]:
        if val.get("administrasi", False):
            st.success("Administrasi Valid")
        else:
            st.error("Administrasi Tidak Valid")

    with cols[1]:
        if val.get("inventory", False):
            st.success("Stok Inventory Tersedia")
        else:
            st.error("Stok Inventory Kurang")

    with cols[2]:
        b_status = val.get("bpjs_status", "UMUM")
        f_level = val.get("faskes_level", 1)
        if b_status == "BPJS":
            st.info(f"{b_status} (Faskes Tk. {f_level})")
        else:
            st.info(f"{b_status}")

    st.markdown("### Rekomendasi Langkah Selanjutnya")
    next_step = data.get("next_step", "STOP")
    
    if next_step == "STOP":
        st.error("STOP: Tidak boleh lanjut ke proses selanjutnya karena validasi gagal (stok habis atau obat tidak ditanggung Fornas di Faskes ini).")
    
    elif next_step == "DISPENSING":
        st.success("LANJUT: Pasien BPJS Tercover, silahkan langsung menuju halaman **Dispensing Obat**.")
        if st.button("Lanjut ke Dispensing", type="primary", key="btn_dispensing"):
            # Simpan data untuk halaman dispensing
            st.session_state["workflow_source"] = "validasi"
            st.session_state["workflow_patient_id"] = st.session_state["validasi_patient_id"]
            st.session_state["workflow_bpjs_status"] = b_status
            st.session_state["workflow_obat_list"] = data.get("obat_list", [])
            st.session_state["workflow_patient_name"] = data.get("patient_name", "")
            st.session_state["workflow_pembayaran_done"] = True  # BPJS = gratis, anggap bayar selesai
            st.switch_page("pages/4_Dispensing.py")
    
    elif next_step == "PEMBAYARAN":
        st.warning("LANJUT: Pasien Umum/Swasta, silahkan lakukan proses **Pembayaran** terlebih dahulu sebelum **Dispensing Obat**.")
        if st.button("Lanjut ke Pembayaran", type="primary", key="btn_pembayaran"):
            # Simpan data untuk halaman pembayaran
            st.session_state["workflow_source"] = "validasi"
            st.session_state["workflow_patient_id"] = st.session_state["validasi_patient_id"]
            st.session_state["workflow_bpjs_status"] = b_status
            st.session_state["workflow_obat_list"] = data.get("obat_list", [])
            st.session_state["workflow_patient_name"] = data.get("patient_name", "")
            st.session_state["workflow_pembayaran_done"] = False
            st.switch_page("pages/5_Pembayaran_Asuransi.py")
        
    st.write("---")
    st.subheader(f"Hasil Analisis AI Resep: {data.get('patient_name')} ({data.get('patient_mrn')})")
    st.markdown(f"**Daftar Obat diresepkan:** {', '.join(data.get('obat_list', []))}")
    st.markdown("### Ringkasan Validasi (Dashboard):")

    summary = data.get("validation_summary", {})
    if summary:
        m1, m2, m3 = st.columns(3)
        diagnosis_label = f"{summary.get('diagnosis', '-')} ({summary.get('diagnosis_code', '-')})"
        m1.metric("Diagnosis", diagnosis_label)
        m2.metric("Stok Obat Ada", summary.get("stok_obat_ada", "-"))
        m3.metric("Administrasi Valid", summary.get("administrasi_valid", "-"))

        m4, m5, m6 = st.columns(3)
        m4.metric("Status BPJS", summary.get("bpjs_status", "-"))
        m5.metric("Faskes", f"Tk. {summary.get('faskes_level', '-')}")
        m6.metric("Rekomendasi Alur", summary.get("rekomendasi_alur", "-"))

        st.markdown("### Detail Cek Obat (Per Poin):")
        obat_checks = summary.get("obat_checks", [])

        if obat_checks:
            for idx, item in enumerate(obat_checks, start=1):
                st.markdown(f"**{idx}. {item.get('obat', '-')}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Resep Qty", item.get("resep_qty", 0))
                c2.metric("Stok Tersedia", item.get("stok_tersedia", 0))
                c3.metric("Stok Ada?", item.get("stok_ada", "-"))
                st.markdown(f"- Status BPJS/Fornas: {item.get('status_bpjs_fornas', '-')}")
                st.markdown(f"- Aturan Minum: {item.get('aturan_minum', '-')}")
                st.write("---")
        else:
            st.info("Tidak ada item obat untuk ditampilkan.")
    else:
        st.code(data.get("ai_analysis", "-"), language="text")

import streamlit as st
import requests
import time
from components.theme import apply_custom_theme

st.set_page_config(page_title="Dispensing", layout="wide")
apply_custom_theme()

st.title("Proses Penyiapan Obat (Dispensing)")
st.markdown("Verifikasi resep, peracikan (jika diperlukan), dan alokasi stok untuk pasien.")


def render_dispensing_preview(data: dict):
    st.success("Resep berhasil diverifikasi.")

    st.subheader("Informasi Pasien & Resep")
    st.write(f"**Nama Pasien:** {data.get('patient_name')}")
    st.caption(data.get("validation_message", "-"))

    stages = data.get("dispensing_stages", {})
    s1, s2, s3 = st.columns(3)
    s1.metric("Penyiapan Obat", stages.get("penyiapan_obat", "-"))
    s2.metric("Peracikan", stages.get("peracikan", "-"))
    s3.metric("Pemberian Obat", stages.get("pemberian_obat", "-"))

    st.markdown("### Detail Penyiapan Obat")
    details = data.get("medicines_detail", [])
    if details:
        for idx, item in enumerate(details, start=1):
            st.markdown(f"**{idx}. {item.get('nama_obat', '-')}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Qty Resep", item.get("qty_resep", 0))
            c2.metric("Sediaan", item.get("sediaan", "-"))
            c3.metric("Perlu Peracikan", item.get("perlu_peracikan", "-"))
            st.markdown(f"- Aturan Minum: {item.get('aturan_minum', '-')}")
            st.write("---")
    else:
        st.markdown("**Daftar Obat:**")
        for med in data.get("medicines", []):
            st.markdown(med)

    st.markdown("### Tahap Peracikan")
    if data.get("need_mixing"):
        st.warning("Terdeteksi obat yang membutuhkan proses peracikan/pelarutan khusus.")
        with st.status("Sedang melakukan proses peracikan..."):
            time.sleep(1)
            st.write("Menyiapkan bahan dan alat...")
            time.sleep(1)
            st.write("Melakukan peracikan sesuai prosedur...")
            time.sleep(1)
            st.write("Verifikasi hasil racikan.")
        st.success("Tahap peracikan selesai.")
    else:
        st.info("Tidak ada item yang memerlukan peracikan. Lanjut finalisasi penyiapan.")

    st.markdown("### Tahap Pemberian Obat")
    checklist = data.get("pemberian_obat_checklist", [])
    if checklist:
        for item in checklist:
            st.markdown(f"- {item}")
    else:
        st.markdown("- Verifikasi identitas pasien")
        st.markdown("- Edukasi aturan minum")
        st.markdown("- Serah obat sesuai etiket")


def render_dispensing_done(comp_data: dict):
    st.write("---")
    st.success("Penyiapan Obat (Dispensing) Selesai! Stok telah diperbarui di database.")

    stages = comp_data.get("dispensing_stages", {})
    s1, s2, s3 = st.columns(3)
    s1.metric("Penyiapan Obat", stages.get("penyiapan_obat", "SELESAI"))
    s2.metric("Peracikan", stages.get("peracikan", "SELESAI / TIDAK DIPERLUKAN"))
    s3.metric("Pemberian Obat", stages.get("pemberian_obat", "SIAP DIBERIKAN KE PASIEN"))

    deductions = comp_data.get("stock_deductions", [])
    if deductions:
        st.subheader("Detail Pengurangan Stok")
        for d in deductions:
            st.markdown(f"- **{d['nama_obat']}**: dikurangi **{d['qty_deducted']}** dari batch `{d['batch_no']}` -- Sisa: **{d['remaining_stock']}**")

    checklist = comp_data.get("pemberian_obat_checklist", [])
    if checklist:
        st.subheader("Checklist Pemberian Obat")
        for item in checklist:
            st.markdown(f"- {item}")

# Cek apakah datang dari workflow (validasi atau pembayaran)
from_workflow = st.session_state.get("workflow_source") in ("validasi", "pembayaran")

if from_workflow:
    wf_patient_id = st.session_state.get("workflow_patient_id", "MR-001")
    wf_bpjs_status = st.session_state.get("workflow_bpjs_status", "UMUM")
    wf_obat_list = st.session_state.get("workflow_obat_list", [])
    wf_patient_name = st.session_state.get("workflow_patient_name", "")
    pembayaran_done = st.session_state.get("workflow_pembayaran_done", False)
    
    source_label = "Validasi (BPJS)" if st.session_state.get("workflow_source") == "validasi" else "Pembayaran"
    st.info(f"**Workflow Aktif** -- Dari: {source_label} | Pasien: **{wf_patient_name}** ({wf_patient_id}) | Status: **{wf_bpjs_status}**")
    
    if wf_bpjs_status in ("UMUM", "SWASTA") and not pembayaran_done:
        st.error("Pasien belum melakukan pembayaran. Silahkan proses pembayaran terlebih dahulu.")
        if st.button("Kembali ke Pembayaran"):
            st.switch_page("pages/5_Pembayaran_Asuransi.py")
        st.stop()
    
    resep_id = st.text_input("ID Registrasi Resep (Contoh: 1 / 2 / 10)", value="1")
    
    if st.button("Mulai Proses Dispensing", type="primary", key="workflow_dispensing"):
        with st.spinner("Memproses resep ke database..."):
            try:
                res = requests.post("http://localhost:8000/api/v1/dispensing/", json={
                    "prescription_id": resep_id
                })
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "error":
                        st.error(data.get("message"))
                    else:
                        st.session_state["dispensing_data"] = data
                        st.session_state["dispensing_step"] = "preview"
                        st.session_state["dispensing_resep_id"] = resep_id
                        st.rerun()
                else:
                    st.error("Gagal melakukan proses. Periksa nomor registrasi resep.")
            except Exception as e:
                st.error(str(e))
    
    # Tampilkan preview dispensing
    if st.session_state.get("dispensing_step") == "preview":
        data = st.session_state["dispensing_data"]
        render_dispensing_preview(data)
        st.info("Obat siap didispensing. Klik tombol di bawah untuk menyelesaikan dan mengurangi stok.")
        
        if st.button("Selesaikan Dispensing & Update Stok", type="primary", key="complete_dispensing"):
            with st.spinner("Memperbarui stok di database..."):
                try:
                    resep_id = st.session_state.get("dispensing_resep_id", "1")
                    comp_res = requests.post("http://localhost:8000/api/v1/dispensing/complete", json={
                        "prescription_id": resep_id
                    })
                    if comp_res.status_code == 200:
                        comp_data = comp_res.json()
                        if comp_data.get("status") == "success":
                            st.session_state["dispensing_step"] = "done"
                            st.session_state["dispensing_complete_data"] = comp_data
                            st.rerun()
                        else:
                            st.error(comp_data.get("message", "Gagal menyelesaikan dispensing."))
                    else:
                        st.error("Gagal menghubungi server untuk update stok.")
                except Exception as e:
                    st.error(str(e))
    
    # Tampilkan hasil akhir
    if st.session_state.get("dispensing_step") == "done":
        comp_data = st.session_state.get("dispensing_complete_data", {})
        render_dispensing_done(comp_data)
        
        st.write("---")
        if st.button("Kembali ke Dashboard", key="back_dashboard"):
            # Bersihkan session workflow
            for key in ["workflow_source", "workflow_patient_id", "workflow_bpjs_status", 
                         "workflow_obat_list", "workflow_patient_name", "workflow_pembayaran_done",
                         "validasi_result", "validasi_done", "validasi_patient_id",
                         "pembayaran_data", "pembayaran_status", "pembayaran_trans_no",
                         "dispensing_data", "dispensing_step", "dispensing_resep_id", "dispensing_complete_data"]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

else:
    # --- Mode Manual (tanpa workflow) ---
    resep_id = st.text_input("ID Registrasi Resep (Contoh: 1 / 2 / 10)", value="1")

    if st.button("Mulai Proses Dispensing", type="primary"):
        with st.spinner("Memproses resep ke database..."):
            try:
                res = requests.post("http://localhost:8000/api/v1/dispensing/", json={
                    "prescription_id": resep_id
                })
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "error":
                        st.error(data.get("message"))
                    else:
                        render_dispensing_preview(data)
                        st.info("Untuk update stok, gunakan alur workflow (validasi/pembayaran) lalu klik Selesaikan Dispensing.")
                else:
                    st.error("Gagal melakukan proses. Periksa nomor registrasi resep.")
            except Exception as e:
                st.error(str(e))

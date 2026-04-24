import streamlit as st
import requests
from components.theme import apply_custom_theme

st.set_page_config(page_title="Dispensing", layout="wide")
apply_custom_theme()

st.title("Proses Penyiapan Obat (Dispensing)")
st.caption("Verifikasi resep, peracikan (jika diperlukan), dan alokasi stok untuk pasien.")


def render_dispensing_preview(data: dict):
    st.success("Resep berhasil diverifikasi.")

    reasoning = data.get("dispensing_reasoning", {}) if isinstance(data.get("dispensing_reasoning"), dict) else {}
    engine = reasoning.get("engine", {}) if isinstance(reasoning.get("engine"), dict) else {}
    model_name = str(engine.get("model", "-")).strip() or "-"
    routed = "YA" if engine.get("routed_to_medgemma") else "TIDAK"
    reasoning_source = str(engine.get("reasoning_source", "-")).strip() or "-"
    stages = data.get("dispensing_stages", {})
    details = data.get("medicines_detail", [])
    ringkasan = str(reasoning.get("ringkasan", "")).strip()
    cara_penyiapan = reasoning.get("cara_penyiapan", []) if isinstance(reasoning.get("cara_penyiapan"), list) else []
    edukasi_penggunaan = reasoning.get("edukasi_penggunaan", []) if isinstance(reasoning.get("edukasi_penggunaan"), list) else []
    peringatan = reasoning.get("peringatan", []) if isinstance(reasoning.get("peringatan"), list) else []
    monitoring_lanjutan = reasoning.get("monitoring_lanjutan", []) if isinstance(reasoning.get("monitoring_lanjutan"), list) else []
    kapan_harus_hubungi_faskes = reasoning.get("kapan_harus_hubungi_faskes", []) if isinstance(reasoning.get("kapan_harus_hubungi_faskes"), list) else []
    raw_response = str(reasoning.get("raw_response", "")).strip()

    st.markdown("### Ringkasan Pasien, Resep, dan Reasoning LLM")
    with st.container(border=True):
        top_left, top_right = st.columns([2, 1])
        with top_left:
            st.markdown(f"**Nama Pasien:** {data.get('patient_name', '-')}")
        with top_right:
            st.caption(f"Model LLM: {model_name}")

        s1, s2, s3 = st.columns(3)
        s1.metric("Penyiapan Obat", stages.get("penyiapan_obat", "-"))
        s2.metric("Peracikan", stages.get("peracikan", "-"))
        s3.metric("Pemberian Obat", stages.get("pemberian_obat", "-"))

        if ringkasan:
            st.success(ringkasan)
        else:
            st.caption("Output ringkasan MedGemma belum tersedia pada sesi ini.")

        if data.get("need_mixing"):
            st.warning("Ada item yang memerlukan peracikan. Ikuti langkah penyiapan LLM secara ketat.")

        st.markdown('<div class="section-title">Detail Obat dan Instruksi</div>', unsafe_allow_html=True)
        row1_left, row1_right = st.columns(2)
        with row1_left:
            with st.container(border=True):
                st.markdown("#### Detail Resep")
                if details:
                    for idx, item in enumerate(details, start=1):
                        st.markdown(
                            f"- **{idx}. {item.get('nama_obat', '-')}** | "
                            f"Qty: {item.get('qty_resep', 0)} | "
                            f"Peracikan: {item.get('perlu_peracikan', '-')}"
                        )
                        st.caption(f"Aturan Minum: {item.get('aturan_minum', '-')}")
                else:
                    for med in data.get("medicines", []):
                        st.markdown(med)

        with row1_right:
            with st.container(border=True):
                st.markdown("#### Cara Penyiapan")
                if cara_penyiapan:
                    for item in cara_penyiapan:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Belum ada output MedGemma untuk bagian ini.")

        st.markdown('<div class="section-title">Konseling dan Monitoring</div>', unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs([
            "Edukasi Penggunaan",
            "Peringatan",
            "Monitoring Lanjutan",
            "Hubungi Faskes",
        ])

        with tab1:
            with st.container(border=True):
                if edukasi_penggunaan:
                    for item in edukasi_penggunaan:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Belum ada output MedGemma untuk bagian ini.")

        with tab2:
            with st.container(border=True):
                if peringatan:
                    for item in peringatan:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Belum ada output MedGemma untuk bagian ini.")

        with tab3:
            with st.container(border=True):
                if monitoring_lanjutan:
                    for item in monitoring_lanjutan:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Belum ada output MedGemma untuk bagian ini.")

        with tab4:
            with st.container(border=True):
                if kapan_harus_hubungi_faskes:
                    for item in kapan_harus_hubungi_faskes:
                        st.markdown(f"- {item}")
                else:
                    st.caption("Belum ada output MedGemma untuk bagian ini.")

        if raw_response:
            with st.expander("Lihat Raw Output MedGemma"):
                st.code(raw_response)


def render_dispensing_done(comp_data: dict):
    st.write("---")
    with st.container(border=True):
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


if "dispensing_manual_done" not in st.session_state:
    st.session_state["dispensing_manual_done"] = False
if "dispensing_manual_data" not in st.session_state:
    st.session_state["dispensing_manual_data"] = None
if "dispensing_manual_resep_id" not in st.session_state:
    st.session_state["dispensing_manual_resep_id"] = "1"

# Cek apakah datang dari workflow validasi
from_workflow = st.session_state.get("workflow_source") == "validasi"

if from_workflow:
    wf_patient_id = st.session_state.get("workflow_patient_id", "MR-001")
    wf_bpjs_status = st.session_state.get("workflow_bpjs_status", "UMUM")
    wf_obat_list = st.session_state.get("workflow_obat_list", [])
    wf_patient_name = st.session_state.get("workflow_patient_name", "")
    wf_prescription_id = str(st.session_state.get("workflow_prescription_id", "")).strip()
    source_label = "Validasi"
    with st.container(border=True):
        st.markdown('<div class="section-title">Workflow Validasi ke Dispensing</div>', unsafe_allow_html=True)
        st.info(f"**Workflow Aktif** -- Dari: {source_label} | Pasien: **{wf_patient_name}** ({wf_patient_id}) | Status: **{wf_bpjs_status}**")

        if not wf_prescription_id:
            st.error("ID resep dari hasil validasi tidak tersedia. Kembali ke validasi lalu jalankan ulang.")
        else:
            st.caption(f"Resep aktif dari validasi: {wf_prescription_id}")

    should_auto_start = (
        bool(wf_prescription_id)
        and st.session_state.get("dispensing_step") not in {"preview", "done"}
    )
    if should_auto_start:
        with st.spinner("Memproses dispensing otomatis dari hasil validasi..."):
            try:
                res = requests.post(
                    "http://localhost:8000/api/v1/dispensing/",
                    json={
                        "prescription_id": wf_prescription_id,
                        "include_llm_reasoning": True,
                    },
                    timeout=60,
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "error":
                        st.error(data.get("message"))
                    else:
                        st.session_state["dispensing_data"] = data
                        st.session_state["dispensing_step"] = "preview"
                        st.session_state["dispensing_resep_id"] = wf_prescription_id
                        st.rerun()
                else:
                    st.error("Gagal melakukan dispensing otomatis dari hasil validasi.")
            except Exception as e:
                st.error(str(e))
    
    # Tampilkan preview dispensing
    if st.session_state.get("dispensing_step") == "preview":
        data = st.session_state["dispensing_data"]
        render_dispensing_preview(data)
        with st.container(border=True):
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
                         "workflow_obat_list", "workflow_patient_name", "workflow_prescription_id",
                         "validasi_result", "validasi_done", "validasi_patient_id",
                         "dispensing_data", "dispensing_step", "dispensing_resep_id", "dispensing_complete_data"]:
                st.session_state.pop(key, None)
            st.switch_page("app.py")

else:
    # --- Mode Manual (tanpa workflow) ---
    run_dispensing = False
    resep_id = str(st.session_state.get("dispensing_manual_resep_id", "1"))

    show_input_card = not (
        st.session_state.get("dispensing_manual_done")
        and st.session_state.get("dispensing_manual_data")
    )

    if show_input_card:
        center_left, center_mid, center_right = st.columns([0.1, 9.8, 0.1])
        with center_mid:
            with st.container(border=True):
                st.markdown("### Masukkan ID Registrasi Resep")
                with st.form("dispensing_manual_form"):
                    resep_id = st.text_input("ID Registrasi Resep (Contoh: 1 / 2 / 10)", value=resep_id)
                    run_dispensing = st.form_submit_button("Mulai Proses Dispensing", type="primary", use_container_width=True)

    if run_dispensing:
        normalized_resep_id = str(resep_id or "").strip()
        if not normalized_resep_id:
            st.error("ID registrasi resep wajib diisi.")
            st.stop()

        with st.spinner("Memproses dispensing dengan auto screening LLM..."):
            try:
                res = requests.post(
                    "http://localhost:8000/api/v1/dispensing/",
                    json={
                        "prescription_id": normalized_resep_id,
                        "include_llm_reasoning": True,
                    },
                    timeout=60,
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "error":
                        st.error(data.get("message"))
                    else:
                        st.session_state["dispensing_manual_data"] = data
                        st.session_state["dispensing_manual_done"] = True
                        st.session_state["dispensing_manual_resep_id"] = normalized_resep_id
                        st.rerun()
                else:
                    st.error("Gagal melakukan proses. Periksa nomor registrasi resep.")
            except Exception as e:
                st.error(str(e))

    if st.session_state.get("dispensing_manual_done") and st.session_state.get("dispensing_manual_data"):
        manual_data = st.session_state["dispensing_manual_data"]

        result_head_left, result_head_right = st.columns([5, 1])
        with result_head_left:
            st.markdown("### Hasil Dispensing")
        with result_head_right:
            if st.button("Dispensing Resep Lain", key="btn_dispensing_resep_lain", use_container_width=True):
                st.session_state["dispensing_manual_data"] = None
                st.session_state["dispensing_manual_done"] = False
                st.rerun()

        render_dispensing_preview(manual_data)
        st.info("Untuk update stok, gunakan alur workflow validasi lalu klik Selesaikan Dispensing.")

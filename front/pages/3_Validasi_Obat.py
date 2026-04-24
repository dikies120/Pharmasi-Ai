import streamlit as st
import requests
import json
from components.theme import apply_custom_theme


def _normalize_header(line: str) -> str:
    cleaned = (line or "").strip().strip("*").strip()
    if cleaned.endswith(":"):
        cleaned = cleaned[:-1].strip()
    return cleaned.lower()


def _strip_thought_prefix(raw_text: str) -> str:
    lines = (raw_text or "").splitlines()
    if not lines:
        return ""

    first_line = lines[0].strip().lower()
    if "thought" in first_line:
        return "\n".join(lines[1:]).strip()
    return (raw_text or "").strip()


def _extract_prescription_and_plan(raw_text: str) -> tuple[str, str]:
    lines = _strip_thought_prefix(raw_text).splitlines()
    if not lines:
        return "", ""

    headers = [_normalize_header(line) for line in lines]

    def _find_idx(candidates: set[str]) -> int:
        for idx, head in enumerate(headers):
            if head in candidates:
                return idx
        return -1

    idx_prescription = _find_idx({"prescriptions", "prescription", "resep"})
    idx_plan = _find_idx({"analysis plan", "rencana analisis"})

    prescription_text = ""
    analysis_plan_text = ""

    if idx_prescription != -1:
        end_idx = idx_plan if idx_plan > idx_prescription else len(lines)
        prescription_text = "\n".join(lines[idx_prescription + 1 : end_idx]).strip()

    if idx_plan != -1:
        analysis_plan_text = "\n".join(lines[idx_plan + 1 :]).strip()

    return prescription_text, analysis_plan_text


def _unwrap_markdown_fence(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""

    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text


def _looks_like_json_text(raw_text: str) -> bool:
    text = _unwrap_markdown_fence(raw_text)
    if not text:
        return False
    try:
        json.loads(text)
        return True
    except Exception:
        return (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]"))


def _to_display_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = _unwrap_markdown_fence(text)
    if _looks_like_json_text(text):
        return ""
    return text


def _to_metric_text(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "YA" if value else "TIDAK"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    text = _to_display_text(value)
    if text:
        return text

    fallback = str(value).strip()
    return fallback if fallback else "-"

st.set_page_config(page_title="Validasi Obat", layout="wide")
apply_custom_theme()

st.title("Validasi Keamanan Obat")
st.caption("Alur: sistem kirim data klinis ke MedGemma, lalu MedGemma melakukan 4 cek klinis (dosis, interaksi, kontraindikasi, alergi).")

run_validation = False
reset_result = False
pasien_id = st.session_state.get("validasi_patient_id", "MR-001")


def _status_chip_class(status_text: str) -> str:
    value = str(status_text or "").strip().lower()
    if any(token in value for token in ("bahaya", "kontra", "stop", "tinggi", "tidak aman")):
        return "status-danger"
    if any(token in value for token in ("perhatian", "warning", "waspada", "monitor")):
        return "status-warning"
    return "status-safe"


def _start_dispensing_workflow_from_validasi(data: dict) -> bool:
    prescription_id = data.get("active_prescription_id")
    if prescription_id in (None, ""):
        return False

    patient_snapshot = data.get("patient_snapshot", {}) if isinstance(data.get("patient_snapshot"), dict) else {}
    medgemma_output = data.get("medgemma_output", {}) if isinstance(data.get("medgemma_output"), dict) else {}
    hasil_per_obat = medgemma_output.get("hasil_per_obat", []) if isinstance(medgemma_output.get("hasil_per_obat"), list) else []

    obat_list = []
    for item in hasil_per_obat:
        if not isinstance(item, dict):
            continue
        obat_name = str(item.get("obat", "")).strip()
        if obat_name:
            obat_list.append(obat_name)

    st.session_state["workflow_source"] = "validasi"
    st.session_state["workflow_patient_id"] = st.session_state.get("validasi_patient_id", "")
    st.session_state["workflow_bpjs_status"] = patient_snapshot.get("bpjs_status", "UMUM")
    st.session_state["workflow_obat_list"] = obat_list
    st.session_state["workflow_patient_name"] = data.get("patient_name", "")
    st.session_state["workflow_prescription_id"] = str(prescription_id)
    return True

if "validasi_done" not in st.session_state:
    st.session_state["validasi_done"] = False
if "validasi_result" not in st.session_state:
    st.session_state["validasi_result"] = None

show_input_card = not (st.session_state.get("validasi_done") and st.session_state.get("validasi_result"))
if show_input_card:
    card_left, card_center, card_right = st.columns([0.1, 9.8, 0.1])
    with card_center:
        with st.container(border=True):
            st.markdown("### Masukkan ID / Nama Pasien")
            with st.form("validasi_form"):
                pasien_id = st.text_input("ID / Nama Pasien", value=pasien_id)
                action_col1, action_col2 = st.columns([2, 1])
                with action_col1:
                    run_validation = st.form_submit_button("Jalankan Validasi", type="primary", use_container_width=True)
                with action_col2:
                    reset_result = st.form_submit_button("Reset", use_container_width=True)

if reset_result:
    st.session_state["validasi_result"] = None
    st.session_state["validasi_done"] = False
    st.session_state["validasi_patient_id"] = ""
    st.success("Hasil validasi dibersihkan.")

if run_validation:
    normalized_patient_id = str(pasien_id or "").strip()
    if not normalized_patient_id:
        st.error("ID / Nama Pasien wajib diisi.")
        st.stop()

    with st.spinner("Mengambil Data Pasien & Mengirim resep ke AI Agent..."):
        try:
            res = requests.post(
                "http://localhost:8000/api/v1/validasi-obat/",
                json={"patient_id": normalized_patient_id},
                timeout=180,
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "error":
                    st.error(data.get("message"))
                    issues = data.get("issues") if isinstance(data.get("issues"), list) else []
                    if issues:
                        st.caption("Detail issue output MedGemma:")
                        for issue in issues:
                            st.markdown(f"- {issue}")

                    expected_count = data.get("expected_obat_count")
                    validated_count = data.get("validated_obat_count")
                    missing_obat = data.get("missing_obat") if isinstance(data.get("missing_obat"), list) else []
                    if expected_count is not None and validated_count is not None:
                        st.warning(f"Cakupan validasi obat: {validated_count}/{expected_count}")
                    if missing_obat:
                        st.caption("Obat yang belum tervalidasi oleh MedGemma:")
                        for obat in missing_obat:
                            st.markdown(f"- {obat}")
                else:
                    st.session_state["validasi_result"] = data
                    st.session_state["validasi_patient_id"] = normalized_patient_id
                    st.session_state["validasi_done"] = True
                    st.rerun()
            else:
                st.error("Gagal melakukan validasi. Periksa koneksi.")
        except Exception as e:
            st.error(str(e))

# Tampilkan hasil validasi jika sudah ada di session
if st.session_state.get("validasi_done") and st.session_state.get("validasi_result"):
    data = st.session_state["validasi_result"]

    result_head_left, result_head_right = st.columns([5, 1])
    with result_head_left:
        st.markdown("### Hasil Validasi")
    with result_head_right:
        if st.button("Validasi Pasien Lain", key="btn_validasi_pasien_lain", use_container_width=True):
            st.session_state["validasi_result"] = None
            st.session_state["validasi_done"] = False
            st.rerun()

    st.write("---")

    medgemma_output = data.get("medgemma_output", {})
    if not isinstance(medgemma_output, dict):
        medgemma_output = {}

    prescription_context = data.get("prescription_context", [])
    if not isinstance(prescription_context, list):
        prescription_context = []

    def _find_prescription_context(obat_name: str) -> dict:
        normalized = str(obat_name or "").strip().lower()
        if not normalized:
            return {}
        for ctx in prescription_context:
            if not isinstance(ctx, dict):
                continue
            ctx_obat = str(ctx.get("obat") or "").strip().lower()
            if not ctx_obat:
                continue
            if ctx_obat == normalized or ctx_obat in normalized or normalized in ctx_obat:
                return ctx
        return {}

    risk_level = _to_display_text(medgemma_output.get("risk_level")) or "-"

    diagnosis = _to_display_text(data.get("diagnosis")) or "-"

    with st.container(border=True):
        st.markdown('<div class="section-title">Ringkasan Pasien</div>', unsafe_allow_html=True)
        rs1, rs2, rs3, rs4 = st.columns(4)
        rs1.metric("Nama", str(data.get("patient_name", "-")))
        rs2.metric("No", str(data.get("patient_mrn", "-")))
        rs3.metric("Risk", risk_level)
        rs4.metric("Diagnosa", diagnosis)

        clinical_engine = data.get("clinical_engine", {}) if isinstance(data.get("clinical_engine"), dict) else {}
        if clinical_engine:
            engine_model = str(clinical_engine.get("model", "-")).strip()
            st.info(f"Model: {engine_model}")

        if not medgemma_output:
            st.warning("Tidak ada output dari MedGemma.")

    with st.container(border=True):
        st.markdown('<div class="section-title">Output Validasi MedGemma</div>', unsafe_allow_html=True)
        st.markdown("### Detail Per Obat")
        hasil_per_obat = medgemma_output.get("hasil_per_obat", [])
        if isinstance(hasil_per_obat, list) and hasil_per_obat:
            for idx, item in enumerate(hasil_per_obat, start=1):
                if not isinstance(item, dict):
                    continue

                obat_name = _to_display_text(item.get("obat")) or "-"
                item_status = _to_display_text(item.get("status")) or "-"
                cek_klinik = item.get("cek_klinik", {}) if isinstance(item.get("cek_klinik"), dict) else {}

                with st.expander(f"{idx}. {obat_name} | Status: {item_status}", expanded=True):
                    chip_class = _status_chip_class(item_status)
                    st.markdown(
                        f'<span class="status-chip {chip_class}">{item_status}</span>',
                        unsafe_allow_html=True,
                    )

                    stok_data = item.get("stok_data", {}) if isinstance(item.get("stok_data"), dict) else {}
                    fallback_ctx = _find_prescription_context(obat_name)
                    fallback_stok_data = fallback_ctx.get("stok_data", {}) if isinstance(fallback_ctx.get("stok_data"), dict) else {}

                    stok_tersedia = item.get("stok_tersedia")
                    if stok_tersedia in (None, ""):
                        stok_tersedia = item.get("stok")
                    if stok_tersedia in (None, ""):
                        stok_tersedia = item.get("stock")
                    if stok_tersedia in (None, ""):
                        stok_tersedia = stok_data.get("stok")
                    if stok_tersedia in (None, ""):
                        stok_tersedia = fallback_ctx.get("stok_tersedia")
                    if stok_tersedia in (None, ""):
                        stok_tersedia = fallback_stok_data.get("stok")

                    resep_qty = item.get("resep_qty")
                    if resep_qty in (None, ""):
                        resep_qty = item.get("qty_resep")
                    if resep_qty in (None, ""):
                        resep_qty = item.get("requested_qty")
                    if resep_qty in (None, ""):
                        resep_qty = item.get("qty")
                    if resep_qty in (None, ""):
                        resep_qty = fallback_ctx.get("resep_qty")

                    stok_col1, stok_col2 = st.columns(2)
                    stok_col1.metric("Stok Tersedia", _to_metric_text(stok_tersedia))
                    stok_col2.metric("Kebutuhan Resep", _to_metric_text(resep_qty))

                    check_rows = [
                        ("Validasi Dosis", "validasi_dosis"),
                        ("Screening Interaksi Obat", "screening_interaksi_obat"),
                        ("Cek Kontraindikasi", "cek_kontraindikasi"),
                        ("Cek Alergi", "cek_alergi"),
                    ]
                    st.markdown('<div class="section-title">Empat Cek Klinis</div>', unsafe_allow_html=True)
                    for label, key in check_rows:
                        check_data = cek_klinik.get(key, {}) if isinstance(cek_klinik.get(key), dict) else {}
                        check_status = _to_display_text(check_data.get("status")) or "-"
                        check_note = _to_display_text(check_data.get("catatan")) or "-"
                        st.markdown(
                            f"- {label}: **{check_status}**  \n"
                            f"  Catatan: {check_note}"
                        )

                    rekomendasi_item = _to_display_text(item.get("rekomendasi"))
                    if rekomendasi_item:
                        st.caption(f"Rekomendasi MedGemma: {rekomendasi_item}")
        else:
            st.warning("MedGemma tidak mengembalikan detail hasil_per_obat.")

    with st.container(border=True):
        analysis = _to_display_text(medgemma_output.get("analysis"))
        recommendation = _to_display_text(medgemma_output.get("recommendation"))
        if analysis or recommendation:
            st.markdown('<div class="section-title">Analisis LLM</div>', unsafe_allow_html=True)
            st.markdown("### Analisis dan Rekomendasi MedGemma")
            with st.container(border=True):
                st.markdown(f"**Analisis:** {analysis or '-'}")
                st.markdown(f"**Rekomendasi:** {recommendation or '-'}")

        raw_medgemma_response = str(data.get("medgemma_raw_response", "")).strip()
        if raw_medgemma_response:
            with st.expander("Lihat Raw Output MedGemma"):
                st.code(raw_medgemma_response)

    with st.container(border=True):
        st.markdown('<div class="section-title">Aksi Berikutnya</div>', unsafe_allow_html=True)
        st.markdown("### Langkah Lanjut")
        next_step = (_to_display_text(medgemma_output.get("next_step")) or "").upper()

        if next_step != "DISPENSING":
            shown_next_step = next_step if next_step else "(kosong)"
            st.warning(f"next_step raw dari MedGemma: {shown_next_step}. Tidak auto-lanjut dispensing.")

        else:
            st.success("Bisa lanjut ke dispensing.")
            if st.button("Lanjut ke Dispensing", type="primary", key="btn_dispensing"):
                if not _start_dispensing_workflow_from_validasi(data):
                    st.error("ID resep aktif tidak ditemukan dari hasil validasi. Jalankan validasi ulang.")
                    st.stop()
                st.switch_page("pages/4_Dispensing.py")

import streamlit as st
import requests
from components.theme import apply_custom_theme

st.set_page_config(page_title="Pembayaran & Asuransi", layout="wide")
apply_custom_theme()

st.title("Sistem Pembayaran dan Verifikasi Asuransi")
st.markdown("Verifikasi jenis bayar dan pembuatan invoice transaksi di kasir farmasi.")

# Cek apakah datang dari workflow validasi
from_workflow = st.session_state.get("workflow_source") == "validasi" and not st.session_state.get("workflow_pembayaran_done", False)

if from_workflow:
    st.info("**Workflow Aktif**: Data pasien otomatis terisi dari hasil Validasi Obat.")
    
    wf_patient_id = st.session_state.get("workflow_patient_id", "MR-001")
    wf_bpjs_status = st.session_state.get("workflow_bpjs_status", "UMUM")
    wf_obat_list = st.session_state.get("workflow_obat_list", [])
    wf_patient_name = st.session_state.get("workflow_patient_name", "")
    
    # Tampilkan ringkasan
    st.markdown(f"**Pasien:** {wf_patient_name} ({wf_patient_id})")
    st.markdown(f"**Status:** {wf_bpjs_status}")
    st.markdown(f"**Obat:** {', '.join(wf_obat_list)}")
    
    # Tentukan jenis pembayaran otomatis
    if wf_bpjs_status == "SWASTA":
        auto_jenis = "Asuransi Swasta"
    else:
        auto_jenis = "Pasien Umum"
    
    col1, col2 = st.columns(2)
    with col1:
        no_kartu = st.text_input("Nomor Kartu / ID Pasien", value=wf_patient_id, disabled=True)
        jenis = st.selectbox("Institusi Penjamin", [auto_jenis], disabled=True)
    
    with col2:
        st.markdown(" ")
        st.markdown(" ")
        if st.button("Proses Pembayaran", type="primary", key="workflow_bayar"):
            with st.spinner("Memproses transaksi pembayaran..."):
                try:
                    # 1. Ambil info tagihan via endpoint asuransi
                    res = requests.post("http://localhost:8000/api/v1/asuransi/", json={
                        "kartu_id": wf_patient_id,
                        "jenis": auto_jenis
                    })
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") == "error":
                            st.error(data.get("verification"))
                        else:
                            st.session_state["pembayaran_data"] = data
                            st.session_state["pembayaran_status"] = "preview"
                    else:
                        st.error("Sistem verifikasi sedang mengalami gangguan.")
                except Exception as e:
                    st.error(str(e))
    
    # Tampilkan preview pembayaran
    if st.session_state.get("pembayaran_status") == "preview":
        data = st.session_state["pembayaran_data"]
        st.write("---")
        st.subheader("Invoice Pembayaran")
        
        st.success(f"Pasien: {data.get('patient_name')} ({data.get('kartu_id')})")
        st.info(f"**Status:** {data.get('verification')}")
        st.warning(f"**Plafon / Keterangan Tagihan:** {data.get('plafon')}")
        
        total = data.get('total_tagihan', 0)
        st.metric("Total Tagihan Pasien", f"Rp {total:,.0f}")
        
        if st.button("Konfirmasi Pembayaran & Catat Transaksi", type="primary", key="konfirmasi_bayar"):
            with st.spinner("Mencatat transaksi ke database..."):
                try:
                    # 2. Proses bayar (catat ke sales + sales_items)
                    pay_res = requests.post("http://localhost:8000/api/v1/asuransi/proses-bayar", json={
                        "kartu_id": wf_patient_id,
                        "jenis": auto_jenis,
                        "total_tagihan": total
                    })
                    if pay_res.status_code == 200:
                        pay_data = pay_res.json()
                        if pay_data.get("status") == "success":
                            st.session_state["pembayaran_status"] = "done"
                            st.session_state["pembayaran_trans_no"] = pay_data.get("transaction_no")
                            st.session_state["workflow_pembayaran_done"] = True
                            st.rerun()
                        else:
                            st.error(pay_data.get("message", "Gagal mencatat pembayaran."))
                    else:
                        st.error("Gagal mencatat pembayaran ke server.")
                except Exception as e:
                    st.error(str(e))
    
    # Tampilkan sukses + button lanjut dispensing
    if st.session_state.get("pembayaran_status") == "done":
        st.write("---")
        trans_no = st.session_state.get("pembayaran_trans_no", "-")
        st.success(f"Pembayaran Berhasil! Transaksi **{trans_no}** telah tercatat ke sistem keuangan.")
        st.balloons()
        
        if st.button("Lanjut ke Dispensing", type="primary", key="btn_to_dispensing"):
            st.session_state["workflow_source"] = "pembayaran"
            st.switch_page("pages/4_Dispensing.py")

else:
    # --- Mode Manual (tanpa workflow) ---
    col1, col2 = st.columns(2)
    with col1:
        no_kartu = st.text_input("Nomor Kartu / ID Pasien", value="MR-001")
        jenis = st.selectbox("Institusi Penjamin", ["BPJS Kesehatan", "Asuransi Swasta", "Pasien Umum"])

    with col2:
        st.markdown(" ")
        st.markdown(" ")
        if st.button("Proses Pembayaran / Verifikasi Asuransi", type="primary"):
            with st.spinner("Memproses transaksi..."):
                try:
                    res = requests.post("http://localhost:8000/api/v1/asuransi/", json={
                        "kartu_id": no_kartu,
                        "jenis": jenis
                    })
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") == "error":
                             st.error(data.get("verification"))
                        else:
                             st.success(f"Pasien: {data.get('patient_name')} ({data.get('kartu_id')})")
                             
                             st.info(f"**Status:** {data.get('verification')}")
                             st.warning(f"**Plafon / Keterangan Tagihan:** {data.get('plafon')}")
                             
                             st.metric("Total Tagihan Pasien", f"Rp {data.get('total_tagihan'):,.0f}")
                             
                             if st.button("Selesaikan Transaksi (Cetak Struk)", key="cetak"):
                                 st.success(f"Transaksi {data.get('trans_no')} telah masuk ke sistem keuangan!")
                    else:
                        st.error("Sistem verifikasi sedang mengalami gangguan.")
                except Exception as e:
                    st.error(str(e))

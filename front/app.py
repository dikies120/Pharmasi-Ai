import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from components.theme import apply_custom_theme

st.set_page_config(page_title="Dashboard Operasional Farmasi", layout="wide")
apply_custom_theme()

st.title("Dashboard Operasional Farmasi")
st.markdown("Dashboard Terpadu: Insight AI, Persediaan Real-Time, Penjualan, & Tren Transaksi")

# 1. Fetch Data
@st.cache_data(ttl=60)
def fetch_analytics():
    try:
        res = requests.get("http://localhost:8000/api/v1/monitoring-stok/analytics")
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {}

def fetch_realtime(nama, lokasi, status):
    params = {}
    if nama: params['nama_obat'] = nama
    if lokasi and lokasi != "Semua Lokasi": params['lokasi'] = lokasi
    if status and status != "Semua": params['status'] = status
    
    try:
        res = requests.get("http://localhost:8000/api/v1/monitoring-stok/realtime", params=params)
        if res.status_code == 200:
            return res.json().get("data", [])
    except:
        pass
    return []

# Bikin 2 tab
tab_dashboard, tab_crud = st.tabs(["Dashboard & Monitoring", "Kelola Stok (CRUD)"])

with tab_dashboard:
    with st.spinner("Memuat data analitik & AI insights..."):
        analytics_resp = fetch_analytics()
        analytics_data = analytics_resp.get("data", {})
        ai_insight = analytics_resp.get("ai_insight", "Insight AI belum tersedia.")

    # ==========================================
    # BAGIAN 1: AI INSIGHT
    # ==========================================
    st.markdown("### Ringkasan Angka AI Agent")
    st.code(ai_insight, language="text")

    st.markdown("---")

    if analytics_data:
        st.markdown("### Ringkasan Performa Farmasi")
        # Transaksi
        transaksi = analytics_data.get("transaksi", {})
        stok = analytics_data.get("stok", {})

        jumlah_tx = transaksi.get("jumlah", 0)
        rev = transaksi.get("revenue", 0)
        avg_ord = transaksi.get("avg_order", 0)
        rev_month = transaksi.get("pendapatan_bulan_ini", 0)

        stok_tertinggi = stok.get("tertinggi") or {}
        stok_terendah = stok.get("terendah") or {}
        label_stok_tinggi = f"{stok_tertinggi.get('nama', '-')} ({stok_tertinggi.get('stok', 0)})"
        label_stok_rendah = f"{stok_terendah.get('nama', '-')} ({stok_terendah.get('stok', 0)})"

        cm1, cm2, cm3, cm4, cm5 = st.columns(5)
        cm1.metric("Total Transaksi", f"{jumlah_tx}x")
        cm2.metric("Pendapatan Bulan Ini", f"Rp {rev_month:,.0f}".replace(",", "."))
        cm3.metric("Total Revenue", f"Rp {rev:,.0f}".replace(",", "."))
        cm4.metric("Stok Tertinggi", label_stok_tinggi)
        cm5.metric("Stok Terendah", label_stok_rendah)
        
        # Pasien Aktif
        top_users = analytics_data.get("user", [])
        if top_users:
            st.caption(f"Pasien paling aktif: {top_users[0]['nama']} ({top_users[0]['kunjungan']} kunjungan)")
        
        st.markdown("---")
        
        col_analitik1, col_analitik2 = st.columns(2)
        
        with col_analitik1:
            st.markdown("#### Penjualan & Jam Sibuk")
            top_selling = analytics_data.get("penjualan", {}).get("top_selling", [])
            if top_selling:
                df_top = pd.DataFrame(top_selling)
                fig_top = px.bar(df_top, x="nama", y="total_terjual", 
                                 title="Top 5 Obat Terlaris",
                                 labels={"nama": "Nama Obat", "total_terjual": "Terjual"},
                                 color_discrete_sequence=['#4CAF50'])
                st.plotly_chart(fig_top, use_container_width=True)
                
        with col_analitik2:
            jam_sibuk = analytics_data.get("waktu", [])
            if jam_sibuk:
                st.markdown("#### ")
                df_jam = pd.DataFrame(jam_sibuk)
                df_jam = df_jam.sort_values(by="jam")
                fig_jam = px.line(df_jam, x="jam", y="transaksi", markers=True,
                                  title="Tren Transaksi (Jam Sibuk)",
                                  labels={"jam": "Jam", "transaksi": "Total TRX"},
                                  color_discrete_sequence=['#FF9800'])
                st.plotly_chart(fig_jam, use_container_width=True)

    st.markdown("---")

    # ==========================================
    # BAGIAN 2: REAL-TIME STOK & PENCARIAN 
    # ==========================================
    st.markdown("### Monitoring Stok Terkini")
    c1, c2, c3 = st.columns(3)
    with c1:
        filter_nama = st.text_input("Pencarian Cepat Obat", placeholder="Ketik nama obat...")
    with c2:
        filter_lokasi = st.selectbox("Filter Lokasi", ["Semua Lokasi", "Gudang 1", "Gudang 2", "Apotek Depan", "IGD", "Rawat Inap"])
    with c3:
        filter_status = st.selectbox("Status", ["Semua", "Stok Kritis", "Aman", "Hampir Expired"])

    realtime_data = fetch_realtime(filter_nama, filter_lokasi, filter_status)

    if realtime_data:
        df_realtime = pd.DataFrame(realtime_data)
        
        # Data Table
        df_display = df_realtime.copy()
        df_display.columns = [col.replace('_', ' ').title() for col in df_display.columns]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Pre-process for graphs
        df_grouped = df_realtime.groupby('nama_obat', as_index=False)['stok'].sum()
        df_grouped = df_grouped.sort_values(by='stok', ascending=False)
        
        col_chart1, col_chart2 = st.columns(2)
        
        # Kritis
        with col_chart1:
            df_kritis = df_grouped[df_grouped['stok'] < 50]
            if not df_kritis.empty:
                fig2 = px.bar(df_kritis, x='stok', y='nama_obat', orientation='h',
                              title="Peringatan: Stok Hampir Habis (< 50)",
                              color='stok', color_continuous_scale="Reds")
                fig2.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.success("Tidak ada obat dengan stok sangat kritis (di bawah 50)")

        # Pergerakan
        with col_chart2:
            movements = analytics_data.get("stok", {}).get("movements", []) if analytics_data else []
            if movements:
                df_mov = pd.DataFrame(movements)
                fig_mov = px.bar(df_mov, x="nama", y=["masuk", "keluar"], barmode="group", 
                                 title="Pergerakan Stok (Masuk vs Keluar)",
                                 labels={"value": "Total"})
                st.plotly_chart(fig_mov, use_container_width=True)
    else:
        st.info("Tidak ada data stok yang sesuai dengan pencarian Anda.")

with tab_crud:
    st.markdown("### Manajemen Data Stok (CRUD)")
    st.write("Gunakan area ini untuk menambah, memperbarui, atau menghapus data inventaris.")
    
    crud_tabs = st.tabs(["Daftar Stok (Read)", "Tambah Obat & Stok (Create)", "Update / Hapus (Update & Delete)"])
    
    semua_data = fetch_realtime("", "Semua Lokasi", "Semua")
    
    with crud_tabs[0]:
        st.subheader("Data Stok Saat Ini")
        if semua_data:
            df_crud = pd.DataFrame(semua_data)
            st.dataframe(df_crud, use_container_width=True, hide_index=True)
        else:
            st.info("Data stok kosong.")
            
    with crud_tabs[1]:
        st.subheader("Tambah Stok Baru")
        with st.form("form_tambah_stok"):
            col1, col2 = st.columns(2)
            with col1:
                input_nama = st.text_input("Nama Obat")
                input_batch = st.text_input("Nomor Batch")
                input_lokasi = st.selectbox("Lokasi Simpan", ["Gudang 1", "Gudang 2", "Apotek Depan", "IGD", "Rawat Inap"])
            with col2:
                input_stok = st.number_input("Kuantitas (Stok)", min_value=1, value=10)
                input_exp = st.date_input("Tanggal Kedaluwarsa")
                
            btn_simpan = st.form_submit_button("Simpan Stok", type="primary")
            if btn_simpan:
                if not input_nama or not input_batch:
                    st.warning("Nama obat dan nomor batch wajib diisi!")
                else:
                    st.success(f"Berhasil (simulasi) menambah stok untuk **{input_nama}** (Batch: {input_batch}) sejumlah {input_stok}!")
                    
    with crud_tabs[2]:
        st.subheader("Update / Hapus Data Stok")
        if semua_data:
            df_edit = pd.DataFrame(semua_data)
            if 'nama_obat' in df_edit.columns:
                obat_list = sorted(list(set(df_edit['nama_obat'].dropna().tolist())))
                pilih_obat = st.selectbox("Pilih Obat untuk Diedit", obat_list)
                
                with st.form("form_update_stok"):
                    c1, c2 = st.columns(2)
                    with c1:
                        tambah_stok = st.number_input("Tambah Stok Masuk (+)", min_value=0, value=0)
                    with c2:
                        kurangi_stok = st.number_input("Kurangi Stok Keluar (-)", min_value=0, value=0)
                    
                    catatan = st.text_area("Catatan Penyesuaian")
                    
                    btn_update = st.form_submit_button("Update Stok Sekarang", type="primary")
                    if btn_update:
                        st.success(f"Berhasil (simulasi) mengupdate stok **{pilih_obat}**! (Tambah: {tambah_stok}, Kurang: {kurangi_stok})")
                        
                st.markdown("---")
                st.markdown(f"**Hapus Data Stok untuk {pilih_obat}**")
                if st.button("Hapus Seluruh Stok Obat Ini", type="secondary"):
                    st.error(f"Berhasil (simulasi) menghapus **{pilih_obat}** dari sistem.")
            else:
                st.warning("Data tidak memiliki kolom 'nama_obat'.")
        else:
            st.info("Sistem belum memiliki data obat.")
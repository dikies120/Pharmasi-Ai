import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

ENDPOINTS = {"graph_medicines": "http://localhost:8000/api/v1/graph/medicines"}

def render_graph_section():
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Tarik Data Analytics Terkini"):
            st.session_state["cache_graph"] = None
            st.rerun()

    try:
        if "cache_graph" not in st.session_state or not st.session_state["cache_graph"]:
            response = requests.get(ENDPOINTS["graph_medicines"], timeout=10)
            if response.status_code == 200:
                st.session_state["cache_graph"] = response.json()
            else:
                st.error("Gagal menarik data grafik dari server.")
                return
        
        data = st.session_state["cache_graph"]
        if not data: return
        
        # Build layout explicitly representing Real-Time vs Analytics
        tab1, tab2 = st.tabs(["Kondisi Real-Time Inventory", "Analitik Deskriptif (Riwayat & Pola)"])
        
        with tab1:
            st.subheader("Distribusi Kondisi Persediaan Real-Time")
            c1, c2 = st.columns(2)
            with c1:
                stock_dist = data.get("stock_distribution", {})
                if sum(stock_dist.values()) > 0:
                    fig = go.Figure(data=[go.Pie(labels=list(stock_dist.keys()), values=list(stock_dist.values()), marker=dict(colors=["#FFB6C6", "#FFDE59", "#95E1D3"]))])
                    fig.update_layout(title="Proporsi Kondisi Stok")
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                exp_dist = data.get("expiry_distribution", {})
                if sum(exp_dist.values()) > 0:
                    fig = go.Figure(data=[go.Pie(labels=list(exp_dist.keys()), values=list(exp_dist.values()), marker=dict(colors=["#FF6B6B", "#51CF66"]))])
                    fig.update_layout(title="Proporsi Risiko Kadaluarsa")
                    st.plotly_chart(fig, use_container_width=True)
            
            meds = data.get("medicines", [])
            st.markdown("**Daftar Kuantitas Inventori (Live)**")
            if meds:
                df = pd.DataFrame(meds)
                df.columns = ["Nama Obat", "Stok Tersedia", "Kadaluarsa Terdekat"]
                st.dataframe(df, use_container_width=True, height=250)

        with tab2:
            st.subheader("Analisis Pola Historis Penjualan & Pergerakan")
            
            sales = data.get("sales_analytics", [])
            if sales:
                df_sales = pd.DataFrame(sales)
                st.markdown("**1. Pola Penjualan Tertinggi Berdasarkan Volume**")
                fig_sales = px.bar(df_sales, x="nama_obat", y="terjual", text="terjual", title="Volume Obat Keluar (Riwayat Transaksi)", color_discrete_sequence=['#3498db'])
                st.plotly_chart(fig_sales, use_container_width=True)
                
                st.markdown("**2. Total Pendapatan per Item Obat**")
                fig_rev = px.bar(df_sales.sort_values(by="pendapatan", ascending=False), x="nama_obat", y="pendapatan", text="pendapatan", title="Tren Pendapatan", color_discrete_sequence=['#2ecc71'])
                st.plotly_chart(fig_rev, use_container_width=True)
            
            movements = data.get("movements_analytics", [])
            if movements:
                df_mov = pd.DataFrame(movements)
                st.markdown("**3. Rasio Pergerakan Stok Keluar vs Masuk (IN/OUT)**")
                fig_mov = px.bar(df_mov, x="nama_obat", y="jumlah", color="tipe", title="Pola Distribusi Logistik Gudang", barmode="group", color_discrete_map={"IN":"#95E1D3", "OUT":"#FFB6C6"})
                st.plotly_chart(fig_mov, use_container_width=True)

    except Exception as e:
        st.error(f"Render Error: {str(e)}")

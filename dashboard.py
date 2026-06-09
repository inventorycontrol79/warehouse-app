import streamlit as st
import pandas as pd
import altair as alt
import io
import os
import xlsxwriter

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Command Center", layout="wide")

# --- PREMIUM CSS (Glassmorphism & Transparency) ---
st.markdown("""
    <style>
    /* 1. Deep Texture Background */
    .stApp { background: #0c0e12; color: #f8fafc; }
    
    /* 2. Premium Header */
    .header-box { padding: 40px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .sabin-plastic { font-size: 55px; font-weight: 900; letter-spacing: 15px; color: #ffffff; text-transform: uppercase; }
    .sub-brand { color: #64748b; letter-spacing: 6px; font-size: 13px; text-transform: uppercase; }
    
    /* 3. Invisible Metrics (Transparent Cards) */
    div[data-testid="stMetric"] { background: transparent; border: none; padding: 0px; }
    .stMetric-value { color: #ffffff !important; font-size: 40px !important; font-weight: 800 !important; }
    .stMetric-label { color: #fbbf24 !important; font-size: 14px !important; text-transform: uppercase; letter-spacing: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<div class='header-box'><div class='sabin-plastic'>SABIN PLASTIC</div><div class='sub-brand'>Warehouse Delivery Tracking System</div></div>", unsafe_allow_html=True)

# --- DATA PROCESSING ---
CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # Sidebar
    st.sidebar.markdown("## ⚙️ COMMAND CENTER")
    sel_loc = st.sidebar.selectbox("Filter Warehouse", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
    sel_stat = st.sidebar.selectbox("Filter Status", ["All"] + sorted(df['Status'].unique().tolist()))
    
    filt = df.copy()
    if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]
    if sel_stat != "All": filt = filt[filt['Status'] == sel_stat]

    # --- SUMMARY (Refined Visibility) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL DO", len(filt))
    m2.metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    m3.metric("PENDING", len(filt[filt['Status']=='Pending']))
    m4.metric("RETURNS", len(filt[filt['Status']=='Return']))

    # --- BLENDED CHART ---
    st.markdown("### Warehouse Performance")
    # Setting transparent background and specific axis colors to match theme
    chart = alt.Chart(filt.groupby('Warehouse_Name').size().reset_index(name='Volume')).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X('Warehouse_Name', title=None, axis=alt.Axis(labelColor='#94a3b8', tickColor='#94a3b8')), 
        y=alt.Y('Volume', title=None, axis=alt.Axis(labelColor='#94a3b8', tickColor='#94a3b8')),
        tooltip=['Warehouse_Name', 'Volume']
    ).properties(height=300, background='transparent').configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # --- TABLE ---
    def color_status(val):
        colors = {'Dispatched': '#10b981', 'Pending': '#f59e0b', 'Return': '#f43f5e'}
        return f'color: {colors.get(val, "#ffffff")}; font-weight: bold'
    
    st.dataframe(filt.style.map(color_status, subset=['Status']), use_container_width=True)
    
    # --- DOWNLOAD ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filt.to_excel(writer, index=False, sheet_name='Report')
    st.download_button("📥 DOWNLOAD EXECUTIVE REPORT", buffer.getvalue(), "SABIN_Logistics.xlsx", "application/vnd.ms-excel")
else:
    st.error("Inventory file not found.")
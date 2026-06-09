import streamlit as st
import pandas as pd
import altair as alt
import io
import os
from xlsxwriter import Workbook

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# --- PREMIUM OBSIDIAN THEME CSS ---
st.markdown("""
    <style>
    .stApp { background: #060911; color: #ffffff; font-family: 'Inter', sans-serif; }
    .brand { font-size: 50px; font-weight: 800; letter-spacing: 12px; color: #ffffff; text-transform: uppercase; margin-bottom: 5px; }
    .sub-brand { color: #64748b; letter-spacing: 5px; font-size: 12px; margin-bottom: 30px; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 25px; border-radius: 4px; }
    .stMetric-value { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<div class='brand'>SABIN</div><div class='sub-brand'>ENTERPRISE LOGISTICS CONTROL</div>", unsafe_allow_html=True)

# --- DATA ENGINE ---
CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # SIDEBAR
    st.sidebar.header("⚙️ OPERATIONS")
    sel_loc = st.sidebar.selectbox("Filter Warehouse", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
    sel_stat = st.sidebar.selectbox("Filter Status", ["All"] + sorted(df['Status'].unique().tolist()))
    
    filt = df.copy()
    if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]
    if sel_stat != "All": filt = filt[filt['Status'] == sel_stat]

    # METRICS
    cols = st.columns(4)
    cols[0].metric("TOTAL LOAD", len(filt))
    cols[1].metric("PENDING", len(filt[filt['Status']=='Pending']))
    cols[2].metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    cols[3].metric("RETURN", len(filt[filt['Status']=='Return']))

    # TELEMETRY CHART
    st.subheader("Warehouse Performance")
    chart = alt.Chart(filt.groupby('Warehouse_Name').size().reset_index(name='Volume')).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X('Warehouse_Name', title=None), y=alt.Y('Volume', title=None)
    ).properties(height=300).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # TABLE WITH COLORS
    def color_status(val):
        color = '#10b981' if val=='Dispatched' else '#f59e0b' if val=='Pending' else '#f43f5e'
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(filt.style.applymap(color_status, subset=['Status']), use_container_width=True)

    # PREMIUM EXCEL EXPORT
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filt.to_excel(writer, index=False, sheet_name='Report')
        workbook  = writer.book
        worksheet = writer.sheets['Report']
        # Apply premium formatting (Status colors)
        status_fmt = workbook.add_format({'bold': True})
        worksheet.conditional_format('B2:B1000', {'type': 'text', 'criteria': 'containing', 'value': 'Pending', 'format': workbook.add_format({'font_color': '#B45309', 'bg_color': '#FEF3C7'})})
        worksheet.conditional_format('B2:B1000', {'type': 'text', 'criteria': 'containing', 'value': 'Dispatched', 'format': workbook.add_format({'font_color': '#047857', 'bg_color': '#D1FAE5'})})

    st.download_button("DOWNLOAD EXECUTIVE REPORT", buffer.getvalue(), "SABIN_Manifest.xlsx", "application/vnd.ms-excel")
else:
    st.error("Data source not found.")
import streamlit as st
import pandas as pd
import altair as alt
import io
import os

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# Styling
st.markdown("""
    <style>
    .stApp { background: #060911; color: #ffffff; }
    .brand { font-size: 50px; font-weight: 800; letter-spacing: 12px; color: #ffffff; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 25px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='brand'>SABIN</div>", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # Filters
    sel_loc = st.sidebar.selectbox("Filter Warehouse", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
    filt = df.copy()
    if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL LOAD", len(filt))
    c2.metric("PENDING", len(filt[filt['Status']=='Pending']))
    c3.metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    c4.metric("RETURN", len(filt[filt['Status']=='Return']))

    # Status Color Logic for Excel/Table
    def get_color(val):
        if val == 'Dispatched': return 'background-color: #10b981; color: white'
        if val == 'Pending': return 'background-color: #f59e0b; color: white'
        if val == 'Return': return 'background-color: #f43f5e; color: white'
        return ''

    # TABLE RENDER (Fixed Attribute Error)
    st.subheader("Live Pipeline")
    # Using .map instead of applymap for compatibility
    st.dataframe(filt.style.map(get_color, subset=['Status']), use_container_width=True)

    # EXCEL EXPORT (Fixed to include full data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filt.to_excel(writer, index=False, sheet_name='Report')
    
    st.download_button("DOWNLOAD EXECUTIVE REPORT", buffer.getvalue(), "SABIN_Manifest.xlsx", "application/vnd.ms-excel")
else:
    st.error("inventory.csv not found.")
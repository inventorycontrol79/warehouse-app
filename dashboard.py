import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# ULTRA-PREMIUM OBSIDIAN GLASS THEME
st.markdown("""
    <style>
    /* Texture & Backdrop */
    .stApp { 
        background: #030406;
        background-image: radial-gradient(circle at 50% 50%, #161b22 0%, #030406 100%);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Monolithic Header */
    .header-box {
        padding: 40px;
        background: rgba(255,255,255,0.02);
        border-bottom: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 30px;
    }
    .sabin-brand {
        font-size: 50px;
        font-weight: 800;
        letter-spacing: 15px;
        text-transform: uppercase;
        color: #ffffff;
        text-shadow: 0 0 20px rgba(255,255,255,0.2);
    }

    /* Glass Cards */
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 25px;
        border-radius: 2px;
        transition: 0.4s;
    }
    div[data-testid="stMetric"]:hover { border-color: #38bdf8; }
    
    /* Text Visibility Fix */
    .stMetric-value { color: #ffffff !important; font-size: 30px !important; }
    .stMetric-label { color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 2px; }
    
    /* Table & Chart Containers */
    .stDataFrame, .stChart {
        background: rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.05);
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# HEADER
st.markdown("<div class='header-box'><div class='sabin-brand'>SABIN</div><div style='color:#64748b; letter-spacing:5px;'>ENTERPRISE LOGISTICS CONTROL</div></div>", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # SIDEBAR LUXURY CONTROLS
    st.sidebar.markdown("## ⚙️ CONFIGURATION")
    sel_loc = st.sidebar.selectbox("Terminal", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
    sel_stat = st.sidebar.selectbox("Status", ["All"] + sorted(df['Status'].unique().tolist()))
    start_d = st.sidebar.date_input("From", df['Date_Issued'].min())
    end_d = st.sidebar.date_input("To", df['Date_Issued'].max())

    # LOGIC
    filt = df.copy()
    if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]
    if sel_stat != "All": filt = filt[filt['Status'] == sel_stat]
    filt = filt[(filt['Date_Issued'].dt.date >= start_d) & (filt['Date_Issued'].dt.date <= end_d)]

    # METRICS
    cols = st.columns(4)
    cols[0].metric("TOTAL LOAD", len(filt))
    cols[1].metric("PENDING", len(filt[filt['Status']=='Pending']))
    cols[2].metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    cols[3].metric("RETURN", len(filt[filt['Status']=='Return']))

    # VISUAL CHART (High contrast)
    st.markdown("### 📊 WAREHOUSE PERFORMANCE")
    perf = filt.groupby('Warehouse_Name').size().reset_index(name='Volume')
    chart = alt.Chart(perf).mark_bar(color='#38bdf8', size=40).encode(
        x=alt.X('Warehouse_Name', title=None),
        y=alt.Y('Volume', title=None),
        tooltip=['Warehouse_Name', 'Volume']
    ).properties(height=350).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # TABLE
    st.dataframe(filt, use_container_width=True)
    
    # DOWNLOAD
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as w: filt.to_excel(w, index=False)
    st.download_button("DOWNLOAD MANIFEST", buffer.getvalue(), "report.xlsx", "application/vnd.ms-excel")
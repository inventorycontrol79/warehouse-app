import streamlit as st
import pandas as pd
import altair as alt
import io
import os
from datetime import datetime
import xlsxwriter

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Logistics", layout="wide")

# --- PREMIUM CSS STYLING ---
st.markdown("""
    <style>
    /* Texture-based dark background */
    .stApp { 
        background: radial-gradient(circle at 50% 50%, #1a1e23 0%, #0d0f12 100%); 
        color: #e2e8f0; 
        font-family: 'Inter', sans-serif; 
    }
    .header-box { padding: 40px; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .sabin-plastic { 
        font-family: 'Montserrat', sans-serif; font-size: 60px; font-weight: 900; 
        letter-spacing: 20px; color: #ffffff; text-transform: uppercase;
        background: linear-gradient(to right, #ffffff, #64748b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sub-brand { color: #94a3b8; letter-spacing: 8px; font-size: 14px; text-transform: uppercase; }
    
    /* Glassmorphism Cards */
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 8px; backdrop-filter: blur(10px); }
    .stMetric-value { color: #ffffff !important; }
    .stMetric-label { color: #cbd5e1 !important; font-size: 12px !important; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown("<div class='header-box'><div class='sabin-plastic'>SABIN PLASTIC</div><div class='sub-brand'>Warehouse Delivery Tracking System</div></div>", unsafe_allow_html=True)

# --- DATA LOAD ---
CSV_FILE = 'inventory.csv'
if not os.path.exists(CSV_FILE):
    st.error("Inventory data missing.")
    st.stop()

df = pd.read_csv(CSV_FILE)
df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')

# --- SIDEBAR (COMMAND CENTER) ---
st.sidebar.markdown("## ⚙️ COMMAND CENTER")
sel_loc = st.sidebar.selectbox("Filter Warehouse", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
sel_stat = st.sidebar.selectbox("Filter Status", ["All"] + sorted(df['Status'].unique().tolist()))
start_d = st.sidebar.date_input("Start Date", df['Date_Issued'].min())
end_d = st.sidebar.date_input("End Date", df['Date_Issued'].max())

# --- FILTERING ---
filt = df.copy()
if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]
if sel_stat != "All": filt = filt[filt['Status'] == sel_stat]
filt = filt[(filt['Date_Issued'].dt.date >= start_d) & (filt['Date_Issued'].dt.date <= end_d)]

# --- SUMMARY METRICS ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("TOTAL DO", len(filt))
m2.metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
m3.metric("PENDING", len(filt[filt['Status']=='Pending']))
m4.metric("MARKED RETURNS", len(filt[filt['Status']=='Return']))

# --- WHATSAPP STATUS ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📱 AUTOMATION")
st.sidebar.success("● WhatsApp Bot: Active")

# --- VISUALS ---
st.subheader("Warehouse Performance Overview")
chart = alt.Chart(filt.groupby('Warehouse_Name').size().reset_index(name='Volume')).mark_bar(color='#38bdf8', cornerRadius=4).encode(
    x=alt.X('Warehouse_Name', title=None), y=alt.Y('Volume', title=None), tooltip=['Warehouse_Name', 'Volume']
).properties(height=300).configure_view(stroke=None).configure_axis(grid=False)
st.altair_chart(chart, use_container_width=True)

# --- TABLE ---
def color_status(val):
    colors = {'Dispatched': '#10b981', 'Pending': '#f59e0b', 'Return': '#f43f5e'}
    return f'color: {colors.get(val, "#ffffff")}; font-weight: bold'

st.dataframe(filt.style.map(color_status, subset=['Status']), use_container_width=True)

# --- PREMIUM EXCEL EXPORT ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # 1. Summary Block
    summary_df = pd.DataFrame({
        'Metric': ['Total DOs', 'Dispatched', 'Pending', 'Returns'],
        'Value': [len(filt), len(filt[filt['Status']=='Dispatched']), len(filt[filt['Status']=='Pending']), len(filt[filt['Status']=='Return'])]
    })
    summary_df.to_excel(writer, sheet_name='Report', startrow=0, index=False)
    # 2. Main Data
    filt.to_excel(writer, sheet_name='Report', startrow=5, index=False)
    
st.download_button("📥 DOWNLOAD EXECUTIVE REPORT", buffer.getvalue(), "SABIN_Logistics_Manifest.xlsx", "application/vnd.ms-excel")
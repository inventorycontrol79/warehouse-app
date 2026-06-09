import streamlit as st
import pandas as pd
import altair as alt
import io
import os

# 1. Page Configuration
st.set_page_config(page_title="SABIN // Operations Command", layout="wide")

# 2. Premium Obsidian Glassmorphism Styling
st.markdown("""
    <style>
    .stApp { background: #060911; color: #ffffff; font-family: 'Inter', sans-serif; }
    .brand-title { font-size: 55px; font-weight: 900; letter-spacing: 18px; color: #ffffff; text-transform: uppercase; margin-bottom: 5px; }
    .sub-title { color: #64748b; letter-spacing: 6px; font-size: 13px; margin-bottom: 40px; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 25px; border-radius: 6px; backdrop-filter: blur(10px); }
    .stMetric-value { color: #ffffff !important; font-size: 32px !important; }
    </style>
""", unsafe_allow_html=True)

# 3. Header
st.markdown("<div class='brand-title'>SABIN</div><div class='sub-title'>ENTERPRISE LOGISTICS CONTROL</div>", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    # Auto-Polish data
    df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # Sidebar Filters
    st.sidebar.header("⚙️ OPERATIONS")
    sel_loc = st.sidebar.selectbox("Filter Warehouse", ["All"] + sorted(df['Warehouse_Name'].unique().tolist()))
    sel_stat = st.sidebar.selectbox("Filter Status", ["All"] + sorted(df['Status'].unique().tolist()))
    
    # Filter Logic
    filt = df.copy()
    if sel_loc != "All": filt = filt[filt['Warehouse_Name'] == sel_loc]
    if sel_stat != "All": filt = filt[filt['Status'] == sel_stat]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL LOAD", len(filt))
    c2.metric("PENDING", len(filt[filt['Status']=='Pending']))
    c3.metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    c4.metric("RETURN", len(filt[filt['Status']=='Return']))

    # Premium Chart
    st.subheader("Warehouse Throughput Performance")
    chart = alt.Chart(filt.groupby('Warehouse_Name').size().reset_index(name='Volume')).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X('Warehouse_Name', title=None), y=alt.Y('Volume', title=None), tooltip=['Warehouse_Name', 'Volume']
    ).properties(height=350).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    # Polished Table
    def style_status(val):
        colors = {'Dispatched': '#10b981', 'Pending': '#f59e0b', 'Return': '#f43f5e'}
        return f'color: {colors.get(val, "#ffffff")}; font-weight: bold'
    
    st.dataframe(filt.style.map(style_status, subset=['Status']), use_container_width=True)

    # Excel Download (Full Manifest)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filt.to_excel(writer, index=False, sheet_name='Manifest')
    st.download_button("DOWNLOAD FULL MANIFEST", buffer.getvalue(), "SABIN_Manifest.xlsx", "application/vnd.ms-excel")

else:
    st.error("Inventory file missing. Please check your file path.")
import streamlit as st
import pandas as pd
import altair as alt
import os

# 1. Page Config
st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# 2. Resilient Styling (Compact CSS)
st.markdown("""
    <style>
    .stApp { background: #060911; color: #ffffff; }
    .sabin-brand { font-size: 40px; font-weight: 800; letter-spacing: 10px; color: #ffffff; text-transform: uppercase; }
    div[data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# 3. Header
st.markdown("<div class='sabin-brand'>SABIN</div>", unsafe_allow_html=True)
st.write("---")

CSV_FILE = 'inventory.csv'

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    # --- AUTO-POLISH DATA ---
    # Strip whitespace, Title Case names, and force date format
    if 'Warehouse_Name' in df.columns:
        df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()
    if 'Date_Issued' in df.columns:
        df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # SIDEBAR
    st.sidebar.header("⚙️ OPERATIONS")
    locs = ["All"] + sorted(df['Warehouse_Name'].unique().tolist())
    sel_loc = st.sidebar.selectbox("Filter Warehouse", locs)
    
    # LOGIC
    filt = df.copy()
    if sel_loc != "All":
        filt = filt[filt['Warehouse_Name'] == sel_loc]
    
    # METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL LOAD", len(filt))
    c2.metric("PENDING", len(filt[filt['Status']=='Pending']))
    c3.metric("DISPATCHED", len(filt[filt['Status']=='Dispatched']))
    c4.metric("RETURN", len(filt[filt['Status']=='Return']))
    
    # CHART
    st.subheader("Performance Telemetry")
    perf = filt.groupby('Warehouse_Name').size().reset_index(name='Volume')
    chart = alt.Chart(perf).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X('Warehouse_Name', title=None),
        y=alt.Y('Volume', title=None),
        tooltip=['Warehouse_Name', 'Volume']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
    
    # TABLE
    st.dataframe(filt, use_container_width=True)
    
    # DOWNLOAD (Using Openpyxl for stability)
    from io import BytesIO
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as w:
        filt.to_excel(w, index=False)
    st.download_button("DOWNLOAD REPORT", buffer.getvalue(), "report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.error("inventory.csv file not found.")
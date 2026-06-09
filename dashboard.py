import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# High-Visibility Styling
st.markdown("""
    <style>
    .stApp { background-color: #060911; color: #ffffff; font-family: 'Inter', sans-serif; }
    div[data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 8px; }
    h1, h2, h3, h4 { color: #f8fafc !important; }
    </style>
""", unsafe_allow_html=True)

st.title("SABIN // Operations Command")

CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    # --- SPECIFIC COLUMN MAPPING ---
    loc_col = 'Warehouse_Name'
    # Fallback to the second column if 'Status' isn't explicitly found
    stat_col = 'Status' if 'Status' in df.columns else df.columns[1]
    
    # Ensure column exists
    if loc_col not in df.columns:
        st.error(f"Error: Expected column '{loc_col}' not found in CSV. Found: {list(df.columns)}")
        st.stop()

    # Sidebar Filter
    locs = ["All"] + list(df[loc_col].unique())
    sel_loc = st.sidebar.selectbox("Filter Warehouse", locs)
    
    filtered_df = df.copy()
    if sel_loc != "All":
        filtered_df = df[df[loc_col] == sel_loc]

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Load", len(filtered_df))
    with m2: st.metric("Pending", len(filtered_df[filtered_df[stat_col]=='Pending']))
    with m3: st.metric("Dispatched", len(filtered_df[filtered_df[stat_col]=='Dispatched']))
    with m4: st.metric("Return", len(filtered_df[filtered_df[stat_col]=='Return']))

    # Visual Performance
    st.subheader("Warehouse Performance Telemetry")
    perf = filtered_df.groupby(loc_col).size().reset_index(name='Volume')
    chart = alt.Chart(perf).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X(loc_col, title='Warehouse'), 
        y=alt.Y('Volume', title='Total Units'),
        tooltip=[loc_col, 'Volume']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # Data Table
    st.dataframe(filtered_df, use_container_width=True)

    # Excel Download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filtered_df.to_excel(writer, index=False)
    
    st.download_button(
        label="Download Executive Report", 
        data=buffer.getvalue(), 
        file_name=f"SABIN_Manifest_{datetime.now().strftime('%Y%m%d')}.xlsx", 
        mime="application/vnd.ms-excel"
    )
else:
    st.error("inventory.csv not found.")
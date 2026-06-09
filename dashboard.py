import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# Styling
st.markdown("""
    <style>
    .stApp { background-color: #060911; color: #ffffff; }
    div[data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("SABIN // Operations Command")

CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    # Ensure columns exist
    df['Date_Issued'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
    
    # SIDEBAR CONTROLS
    st.sidebar.header("Operations Filter")
    
    # 1. Warehouse Filter
    loc_col = 'Warehouse_Name'
    warehouses = ["All"] + sorted(df[loc_col].unique().tolist())
    sel_loc = st.sidebar.selectbox("Filter Warehouse", warehouses)
    
    # 2. Status Filter
    stat_col = 'Status'
    statuses = ["All"] + sorted(df[stat_col].unique().tolist())
    sel_stat = st.sidebar.selectbox("Filter Status", statuses)
    
    # 3. Date Filter
    start_d = st.sidebar.date_input("Start Date", df['Date_Issued'].min())
    end_d = st.sidebar.date_input("End Date", df['Date_Issued'].max())
    
    # APPLY FILTERS
    filtered_df = df.copy()
    if sel_loc != "All": filtered_df = filtered_df[filtered_df[loc_col] == sel_loc]
    if sel_stat != "All": filtered_df = filtered_df[filtered_df[stat_col] == sel_stat]
    filtered_df = filtered_df[(filtered_df['Date_Issued'].dt.date >= start_d) & (filtered_df['Date_Issued'].dt.date <= end_d)]

    # METRICS
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Load", len(filtered_df))
    with m2: st.metric("Pending", len(filtered_df[filtered_df[stat_col]=='Pending']))
    with m3: st.metric("Dispatched", len(filtered_df[filtered_df[stat_col]=='Dispatched']))
    with m4: st.metric("Return", len(filtered_df[filtered_df[stat_col]=='Return']))

    # VISUAL PERFORMANCE (Grouped correctly to avoid duplicates)
    st.subheader("Warehouse Performance")
    perf = filtered_df.groupby(loc_col).size().reset_index(name='Volume')
    chart = alt.Chart(perf).mark_bar(color='#38bdf8', cornerRadius=4).encode(
        x=alt.X(loc_col, title='Warehouse'), 
        y=alt.Y('Volume', title='Total Units'),
        tooltip=[loc_col, 'Volume']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # DATA TABLE
    st.dataframe(filtered_df, use_container_width=True)

    # EXCEL DOWNLOAD
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        filtered_df.to_excel(writer, index=False)
    
    st.download_button("Download Report", data=buffer.getvalue(), file_name="report.xlsx", mime="application/vnd.ms-excel")
else:
    st.error("inventory.csv not found.")
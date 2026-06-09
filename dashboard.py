import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="SABIN // Command Center", layout="wide")

# High-Visibility Styling
st.markdown("""
    <style>
    .stApp { background-color: #060911; color: #ffffff; font-family: 'Inter', sans-serif; }
    .metric-value { font-size: 32px !important; color: #ffffff !important; }
    .metric-label { color: #cbd5e1 !important; font-size: 12px !important; }
    div[data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; padding: 20px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("SABIN // Operations Command")

CSV_FILE = 'inventory.csv'
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    
    # Simple Filters
    st.sidebar.header("Controls")
    locs = ["All"] + list(df['Location'].unique())
    sel_loc = st.sidebar.selectbox("Filter Location", locs)
    
    filtered_df = df.copy()
    if sel_loc != "All":
        filtered_df = df[df['Location'] == sel_loc]

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Load", len(filtered_df))
    with m2: st.metric("Pending", len(filtered_df[filtered_df['Status']=='Pending']))
    with m3: st.metric("Dispatched", len(filtered_df[filtered_df['Status']=='Dispatched']))
    with m4: st.metric("Return", len(filtered_df[filtered_df['Status']=='Return']))

    # Visual Warehouse Performance
    st.subheader("Warehouse Performance")
    perf = filtered_df.groupby('Location').size().reset_index(name='Volume')
    chart = alt.Chart(perf).mark_bar(color='#38bdf8').encode(
        x='Location', y='Volume', tooltip=['Location', 'Volume']
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # Data Table
    st.subheader("Live Pipeline")
    st.dataframe(filtered_df, use_container_width=True)

    # Excel Download Engine (RE-ADDED)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Report')
    
    st.download_button(
        label="Download Report as Excel",
        data=excel_buffer.getvalue(),
        file_name=f"SABIN_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Please upload a file to begin.")
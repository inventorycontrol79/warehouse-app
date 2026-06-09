import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 1. Page Configuration
st.set_page_config(page_title="SABIN // Enterprise Command", layout="wide")

# 2. CSS Injector (Same Premium Obsidian Theme)
st.markdown("""
    <style>
    .stApp { background-color: #060911; color: #f1f5f9; font-family: 'Inter', sans-serif; }
    .brand-frame { padding: 40px 50px; border-left: 4px solid #f8fafc; background: rgba(255, 255, 255, 0.03); margin-bottom: 30px; }
    .brand-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 42px; font-weight: 800; letter-spacing: 12px; text-transform: uppercase; color: #ffffff; }
    .brand-subtitle { font-size: 12px; text-transform: uppercase; letter-spacing: 5px; color: #64748b; margin-top: 12px; }
    div[data-testid="stMetric"] { background: rgba(15, 23, 42, 0.45); border: 1px solid rgba(255, 255, 255, 0.05); padding: 20px; }
    </style>
""", unsafe_allow_html=True)

# 3. Branding
st.markdown("<div class='brand-frame'><div class='brand-title'>SABIN</div><div class='brand-subtitle'>Logistics Intelligence & Corporate Operations</div></div>", unsafe_allow_html=True)

# 4. Data Loading
CSV_FILE = 'inventory.csv'
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=['Location', 'Status', 'Date_Issued', 'Last_4', 'DO_Number']).to_csv(CSV_FILE, index=False)
df = pd.read_csv(CSV_FILE)

# 5. Definitions & Filters (Defined BEFORE usage)
LOCATION_COLUMN = 'Location'
STATUS_COLUMN = 'Status'
DATE_COLUMN = 'Date_Issued'

# Sidebar Controls
uploaded_file = st.sidebar.file_uploader("Import ERP Manifest", type=['csv', 'xlsx'])
if uploaded_file:
    uploaded_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    uploaded_df.to_csv(CSV_FILE, index=False)
    st.rerun()

# Date Filtering Logic
if DATE_COLUMN in df.columns:
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
    min_d, max_d = df[DATE_COLUMN].min(), df[DATE_COLUMN].max()
    start_date = st.sidebar.date_input("From Date", min_d if pd.notnull(min_d) else datetime.today())
    end_date = st.sidebar.date_input("To Date", max_d if pd.notnull(max_d) else datetime.today())
    filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
else:
    filtered_df = df

# 6. Performance Telemetry Chart
st.markdown("<h4 style='font-size:12px; text-transform:uppercase; color:#94a3b8;'>Warehouse Performance Telemetry</h4>", unsafe_allow_html=True)
if not filtered_df.empty and LOCATION_COLUMN in filtered_df.columns:
    perf_data = filtered_df.groupby(LOCATION_COLUMN).size().reset_index(name='Volume')
    chart = alt.Chart(perf_data).mark_bar(cornerRadius=2).encode(
        x=alt.X(LOCATION_COLUMN, title=None),
        y=alt.Y('Volume', title=None),
        color=alt.value('#64748b')
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)

# 7. Metrics
cols = st.columns(4)
count_d = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Dispatched']) if STATUS_COLUMN in filtered_df.columns else 0
count_p = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Pending']) if STATUS_COLUMN in filtered_df.columns else len(filtered_df)
count_r = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Return']) if STATUS_COLUMN in filtered_df.columns else 0

with cols[0]: st.metric("Total Load Profile", len(filtered_df))
with cols[1]: st.metric("Pending Queue", count_p)
with cols[2]: st.metric("Dispatched Volume", count_d)
with cols[3]: st.metric("Return Records", count_r)

# 8. Dataframe
st.dataframe(filtered_df, use_container_width=True)
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# [Style and Config remain the same as the previous premium version...]
st.set_page_config(page_title="SABIN // Enterprise Command", layout="wide")

# ... (Insert the full CSS block here from the previous message) ...

# [Keep your Header and Sidebar logic exactly as it was]
# ...

# 1. DEFINE FILTERED_DF BEFORE THE CHART (This fixes your NameError)
if DATE_COLUMN in df.columns:
    df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
    clean_dates = df[DATE_COLUMN].dropna()
    if not clean_dates.empty:
        start_date = st.sidebar.date_input("From Date", min(clean_dates))
        end_date = st.sidebar.date_input("To Date", max(clean_dates))
        filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
    else: filtered_df = df
else: filtered_df = df

# 2. NOW ADD THE CHART (It now has access to the defined filtered_df)
st.markdown("<h4 style='font-family:Inter; font-size:12px; text-transform:uppercase; letter-spacing:2px; color:#94a3b8; margin-bottom:20px;'>Warehouse Performance Telemetry</h4>", unsafe_allow_html=True)

if not filtered_df.empty and 'Location' in filtered_df.columns:
    perf_data = filtered_df.groupby('Location').size().reset_index(name='Volume')
    chart = alt.Chart(perf_data).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X('Location', title=None, axis=alt.Axis(labelColor='#64748b', tickColor='#334155')),
        y=alt.Y('Volume', title=None, axis=alt.Axis(gridColor='#1e293b', labelColor='#64748b')),
        color=alt.value('#64748b') # Sophisticated slate color
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)

# 3. METRIC CARDS
count_dispatched = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Dispatched']) if STATUS_COLUMN in filtered_df.columns else 0
count_pending = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Pending']) if STATUS_COLUMN in filtered_df.columns else len(filtered_df)
count_return = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Return']) if STATUS_COLUMN in filtered_df.columns else 0

m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("Total Load Profile", f"{len(filtered_df):,}")
with m2: st.metric("Pending Queue", f"{count_pending:,}")
with m3: st.metric("Dispatched Volume", f"{count_dispatched:,}")
with m4: st.metric("Return Records", f"{count_return:,}")

# 4. DATAFRAME
# ... (Rest of your code remains the same) ...
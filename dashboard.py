import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- [UI Injector: Same as before, now with Chart Styling] ---
st.markdown("""
    <style>
    /* ... (Keeping the previously defined styles) ... */
    .stChart { background: rgba(15, 23, 42, 0.2); border: 1px solid rgba(255,255,255,0.05); padding: 10px; }
    </style>
""", unsafe_allow_html=True)

# [Branding and Filter Logic... (Same as before)]

# --- [ADD THIS CHART BLOCK BEFORE THE DATAFRAME] ---
st.markdown("<h4 style='font-family:Inter; font-size:12px; text-transform:uppercase; letter-spacing:2px; color:#94a3b8; margin-bottom:20px;'>Warehouse Performance Telemetry</h4>", unsafe_allow_html=True)

if not filtered_df.empty and 'Location' in filtered_df.columns:
    # Prepare performance data
    perf_data = filtered_df.groupby('Location').size().reset_index(name='Volume')
    
    # Premium Chart Design
    chart = alt.Chart(perf_data).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X('Location', title=None, axis=alt.Axis(labelColor='#64748b', tickColor='#334155')),
        y=alt.Y('Volume', title=None, axis=alt.Axis(gridColor='#1e293b', labelColor='#64748b')),
        color=alt.Color('Volume', scale=alt.Scale(scheme='greys'), legend=None)
    ).properties(height=250)
    
    st.altair_chart(chart, use_container_width=True)

# [Proceed with DataFrame and Download Button...]
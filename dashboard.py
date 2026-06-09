import streamlit as st
import pandas as pd
import altair as alt
import io
import os

# --- PREMIUM CONFIG ---
st.set_page_config(page_title="SABIN // Operations", layout="wide")

# High-Visibility CSS
st.markdown("""
    <style>
    .stApp { background: #060911; color: #ffffff; }
    .sabin-brand { font-size: 48px; font-weight: 800; letter-spacing: 12px; text-transform: uppercase; color: #ffffff; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 25px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- CHART THEME ---
def premium_theme():
    return {
        "config": {
            "background": "transparent",
            "axis": {"domainColor": "#475569", "gridColor": "#1e293b", "labelColor": "#94a3b8", "titleColor": "#f8fafc"},
            "mark": {"color": "#38bdf8"}
        }
    }
alt.themes.register("premium", premium_theme)
alt.themes.enable("premium")

# --- DATA PROCESSING ---
CSV_FILE = 'inventory.csv'
df = pd.read_csv(CSV_FILE)
df['Warehouse_Name'] = df['Warehouse_Name'].astype(str).str.strip().str.title()

# --- UI COMPONENTS ---
st.markdown("<div class='sabin-brand'>SABIN</div>", unsafe_allow_html=True)

# Performance Chart (High End, Dark Theme)
perf = df.groupby('Warehouse_Name').size().reset_index(name='Volume')
chart = alt.Chart(perf).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
    x=alt.X('Warehouse_Name', title=None),
    y=alt.Y('Volume', title=None),
    tooltip=['Warehouse_Name', 'Volume']
).properties(height=300)
st.altair_chart(chart, use_container_width=True)

# Status Color Function
def color_status(val):
    color = '#cbd5e1' # Default
    if val == 'Dispatched': color = '#10b981' # Emerald
    elif val == 'Pending': color = '#f59e0b' # Amber
    elif val == 'Return': color = '#f43f5e' # Rose
    return f'color: {color}; font-weight: bold'

# Display Table with Conditional Coloring
st.subheader("Live Pipeline")
st.dataframe(df.style.applymap(color_status, subset=['Status']), use_container_width=True)
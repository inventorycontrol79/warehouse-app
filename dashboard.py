import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Al Quoz & Abu Dhabi Warehouse Logistics", layout="wide")

# Visually Catchy Dark Premium Theme CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ecf0f1; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc !important; }
    div[data-testid="stMetricLabel"] { color: #a0aec0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Inventory & Logistics Portal")
st.markdown("---")

try:
    df = pd.read_csv('inventory.csv')
    
    # 🎯 MATCHED TO YOUR CSV HEADING EXACLY
    DATE_COLUMN = 'Date_Issued' 
    
    if DATE_COLUMN in df.columns:
        # Convert the Date_Issued column to a proper Python date format safely
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN]).dt.date
        
        # Sidebar Filtering UI Setup
        st.sidebar.header("🎯 Filter Control Center")
        min_date = min(df[DATE_COLUMN])
        max_date = max(df[DATE_COLUMN])
        
        start_date = st.sidebar.date_input("Start Date", min_date)
        end_date = st.sidebar.date_input("End Date", max_date)
        
        # 🔗 Dynamic Link: This filters the data matrix instantly on selection
        filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
    else:
        # Quick fallback warning in case there's an unforeseen structural change
        st.sidebar.warning(f"⚠️ Column '{DATE_COLUMN}' not found. Check your CSV columns: {list(df.columns)}")
        filtered_df = df

    # KPI Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records Found", len(filtered_df))
    with col2:
        # Change 'Quantity' to your specific weight or item stock count column header if needed
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else "N/A"
        st.metric("Total Quantity", total_stock)
    with col3:
        st.metric("Status", "Active Sync")

    # Interactive Table (Directly linked to filtered data)
    st.markdown("### 📋 Filtered Warehouse Records")
    st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ 'inventory.csv' not found. Ensure it is placed inside the 'warehouse-tracker' directory.")
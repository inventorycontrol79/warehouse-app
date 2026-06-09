import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Al Quoz & Abu Dhabi Warehouse Logistics", layout="wide")

# Premium Dark Theme UI Style
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
    
    DATE_COLUMN = 'Date_Issued' 
    
    if DATE_COLUMN in df.columns:
        # CRITICAL FIX: errors='coerce' prevents crashes by safely handling blank/corrupted rows
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
        
        # Drop rows where the date is completely missing just for the calendar range calculation
        clean_dates = df[DATE_COLUMN].dropna()
        
        if not clean_dates.empty:
            min_date = min(clean_dates)
            max_date = max(clean_dates)
            
            # Sidebar UI
            st.sidebar.header("🎯 Filter Control Center")
            start_date = st.sidebar.date_input("Start Date", min_date)
            end_date = st.sidebar.date_input("End Date", max_date)
            
            # Filter rows (also handles rows without valid dates safely)
            filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
        else:
            st.sidebar.warning("⚠️ No valid dates found in the column to filter by.")
            filtered_df = df
    else:
        st.sidebar.warning(f"⚠️ Column '{DATE_COLUMN}' not found. Available columns: {list(df.columns)}")
        filtered_df = df

    # KPI Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records Found", len(filtered_df))
    with col2:
        # Change 'Quantity' to your stock column name if named differently
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else "N/A"
        st.metric("Total Quantity", total_stock)
    with col3:
        st.metric("Status", "Active Sync")

    # Interactive Table Layout
    st.markdown("### 📋 Filtered Warehouse Records")
    st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ 'inventory.csv' not found in your repository.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
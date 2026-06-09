import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Warehouse Logistics Portal", layout="wide")

# Premium Dark Theme
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ecf0f1; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc !important; }
    div[data-testid="stMetricLabel"] { color: #a0aec0 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Inventory Portal")
st.markdown("---")

try:
    df = pd.read_csv('inventory.csv')
    
    st.sidebar.header("🎯 Filter Control Center")

    # 1. WAREHOUSE LOCATION FILTER
    LOCATION_COLUMN = 'Location' 
    if LOCATION_COLUMN in df.columns:
        unique_locations = list(df[LOCATION_COLUMN].unique())
        selected_location = st.sidebar.selectbox("Select Warehouse Location", unique_locations)
        df = df[df[LOCATION_COLUMN] == selected_location]

    # 2. INTERACTIVE STATUS FILTER (Gives them the option to pick 'Pending')
    # Change 'Status' below if your column heading is different (e.g., 'Order_Status')
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        # Create an 'All' option, followed by 'Pending', then any other statuses found in your file
        existing_statuses = list(df[STATUS_COLUMN].dropna().unique())
        
        # Ensure 'Pending' is easily visible in the list if it exists
        if 'Pending' in existing_statuses:
            existing_statuses.remove('Pending')
            status_options = ["All", "Pending"] + existing_statuses
        else:
            status_options = ["All"] + existing_statuses

        # This gives them the dropdown option in the sidebar
        selected_status = st.sidebar.selectbox("Filter by Status", status_options)
        
        # If they choose anything other than "All", filter the table dynamically
        if selected_status != "All":
            df = df[df[STATUS_COLUMN] == selected_status]

    # 3. DATE FILTER
    DATE_COLUMN = 'Date_Issued' 
    if DATE_COLUMN in df.columns:
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
        clean_dates = df[DATE_COLUMN].dropna()
        
        if not clean_dates.empty:
            start_date = st.sidebar.date_input("Start Date", min(clean_dates))
            end_date = st.sidebar.date_input("End Date", max(clean_dates))
            filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
        else:
            filtered_df = df
    else:
        filtered_df = df
            
    # KPI Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Records on Screen", len(filtered_df))
    with col2:
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else "N/A"
        st.metric("Total Quantity", total_stock)
    with col3:
        st.metric("Portal Status", "Live & Synced")

    # Interactive Table Layout
    st.markdown("### 📋 Active Warehouse Records")
    st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ 'inventory.csv' not found. Please verify it is in your folder.")
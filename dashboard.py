import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Configuration & Premium Theme Styling
st.set_page_config(page_title="Warehouse Logistics Portal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ecf0f1; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00ffcc !important; }
    div[data-testid="stMetricLabel"] { color: #a0aec0 !important; }
    .stSelectbox label, .stDateInput label { color: #00ffcc !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Inventory & Logistics Portal")
st.markdown("---")

# 🟢 Helper Function to Color-Code Row Backgrounds Based on Status
def style_status_rows(row):
    status = str(row['Status']).strip()
    # Create a default style list matching the number of columns in the row
    styles = [''] * len(row)
    
    # Define our colors (Using bright text so it's perfectly visible over dark backgrounds)
    if status == 'Dispatched':
        color_style = 'background-color: #0d5c3a; color: #ffffff; font-weight: bold;' # Royal Green
    elif status == 'Return':
        color_style = 'background-color: #8c1d1d; color: #ffffff; font-weight: bold;' # Deep Red
    elif status == 'Pending':
        color_style = 'background-color: #b37400; color: #ffffff; font-weight: bold;' # Amber Gold
    else:
        return styles # No changes for other statuses
        
    # Apply the color style across every single cell in that specific row
    return [color_style for _ in range(len(row))]

try:
    # 2. Read Data
    df = pd.read_csv('inventory.csv')
    st.sidebar.header("🎯 Filter Control Center")

    # 3. SMART WAREHOUSE CONTROLLER
    LOCATION_COLUMN = 'Warehouse_Name' 
    if LOCATION_COLUMN in df.columns:
        df[LOCATION_COLUMN] = df[LOCATION_COLUMN].astype(str).str.strip()
        unique_locations = sorted(list(df[LOCATION_COLUMN].unique()))
        
        url_params = st.query_params
        
        if "warehouse" in url_params and url_params["warehouse"] in unique_locations:
            target_warehouse = url_params["warehouse"]
            st.sidebar.info(f"📍 Location Locked: **{target_warehouse}**")
            df = df[df[LOCATION_COLUMN] == target_warehouse]
        else:
            master_options = ["All Locations"] + unique_locations
            selected_location = st.sidebar.selectbox("Select Warehouse Location (Master)", master_options)
            
            if selected_location != "All Locations":
                df = df[df[LOCATION_COLUMN] == selected_location]
                st.query_params["warehouse"] = selected_location
            else:
                st.query_params["warehouse"] = "All"

    # 4. INTERACTIVE STATUS FILTER
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
        existing_statuses = list(df[STATUS_COLUMN].unique())
        
        if 'Pending' in existing_statuses:
            existing_statuses.remove('Pending')
            status_options = ["All", "Pending"] + existing_statuses
        else:
            status_options = ["All"] + existing_statuses

        selected_status = st.sidebar.selectbox("Filter by Status", status_options)
        if selected_status != "All":
            df = df[df[STATUS_COLUMN] == selected_status]

    # 5. DATE FILTER
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
            
    # 6. KPI Dashboard Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Records on Screen", len(filtered_df))
    with col2:
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else "N/A"
        st.metric("Total Quantity", total_stock)
    with col3:
        st.metric("Portal Status", "Live Sync Active")

    # 7. Interactive Live Data Table with Applied Background Colors
    st.markdown("### 📋 Active Warehouse Records")
    
    if STATUS_COLUMN in filtered_df.columns and len(filtered_df) > 0:
        # Apply the styling rule row-by-row
        styled_df = filtered_df.style.apply(style_status_rows, axis=1)
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ 'inventory.csv' not found.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Configuration & Custom Theme Styling
st.set_page_config(page_title="Warehouse Logistics Portal", layout="wide")

# Custom CSS for a visually catchy, premium dark logistics theme
st.markdown("""
    <style>
    .stApp { 
        background-color: #0e1117; 
        color: #ecf0f1; 
    }
    div[data-testid="stMetricValue"] { 
        font-size: 28px; 
        color: #00ffcc !important; 
    }
    div[data-testid="stMetricLabel"] { 
        color: #a0aec0 !important; 
    }
    .stSelectbox label, .stDateInput label {
        color: #00ffcc !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Inventory & Logistics Portal")
st.markdown("---")

try:
    # 2. Read Data from Cloud Repository
    df = pd.read_csv('inventory.csv')
    
    st.sidebar.header("🎯 Filter Control Center")

    # 3. WAREHOUSE LOCATION FILTER (With automatic whitespace cleanup)
    LOCATION_COLUMN = 'Location' 
    if LOCATION_COLUMN in df.columns:
        # Convert to string and strip out hidden spaces that cause duplicates
        df[LOCATION_COLUMN] = df[LOCATION_COLUMN].astype(str).str.strip()
        
        # Sort names alphabetically (Abu Dhabi, Al Quoz, DIP, Sharjah)
        unique_locations = sorted(list(df[LOCATION_COLUMN].unique()))
        
        selected_location = st.sidebar.selectbox("Select Warehouse Location", unique_locations)
        df = df[df[LOCATION_COLUMN] == selected_location]

    # 4. INTERACTIVE STATUS FILTER (With automatic whitespace cleanup)
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        # Strip out hidden spaces from status values
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
        
        existing_statuses = list(df[STATUS_COLUMN].unique())
        
        # Prioritize "Pending" at the top of the dropdown list right under "All"
        if 'Pending' in existing_statuses:
            existing_statuses.remove('Pending')
            status_options = ["All", "Pending"] + existing_statuses
        else:
            status_options = ["All"] + existing_statuses

        selected_status = st.sidebar.selectbox("Filter by Status", status_options)
        
        if selected_status != "All":
            df = df[df[STATUS_COLUMN] == selected_status]

    # 5. DATE FILTER (With crash protection for bad/blank dates)
    DATE_COLUMN = 'Date_Issued' 
    if DATE_COLUMN in df.columns:
        # errors='coerce' safely handles blank rows or mistyped text without crashing the app
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
        # Dynamically calculate total stock sum if 'Quantity' column exists
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else "N/A"
        st.metric("Total Quantity", total_stock)
    with col3:
        st.metric("Portal Status", "Live Sync Active")

    # 7. Interactive Live Data Table
    st.markdown("### 📋 Active Warehouse Records")
    st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ 'inventory.csv' not found. Please ensure it is uploaded inside the 'warehouse-tracker' directory via GitHub Desktop.")
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Configuration & Custom Theme Layout
st.set_page_config(page_title="Warehouse Logistics Master Portal", layout="wide")

# Custom CSS for an Ultra-Premium Dark Theme with glowing indicators and clean layouts
st.markdown("""
    <style>
    /* Main Background Elements */
    .stApp { 
        background-color: #0b0e14; 
        color: #f1f5f9; 
    }
    /* Executive Summary Block Styling */
    .summary-box {
        background: #111827;
        padding: 18px 25px;
        border-radius: 10px;
        border-left: 5px solid #00ffcc;
        border-top: 1px solid #1f2937;
        border-right: 1px solid #1f2937;
        border-bottom: 1px solid #1f2937;
        margin-bottom: 25px;
    }
    .summary-title {
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #94a3b8;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .summary-grid {
        display: flex;
        gap: 30px;
        flex-wrap: wrap;
    }
    .summary-item {
        font-size: 16px;
        font-weight: 500;
    }
    /* KPI Metric Cards Styling */
    div[data-testid="stMetricValue"] { 
        font-size: 32px; 
        font-weight: 700;
        color: #00ffcc !important; 
    }
    div[data-testid="stMetricLabel"] { 
        color: #94a3b8 !important; 
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 11px;
    }
    div[data-testid="stMetric"] {
        background-color: #111827;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #1f2937;
    }
    /* Input Form Label Adjustments */
    .stSelectbox label, .stDateInput label { 
        color: #94a3b8 !important; 
        font-weight: 600; 
    }
    hr {
        border: 0;
        height: 1px;
        background: linear-gradient(to right, #00ffcc, transparent);
        margin: 20px 0px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Operations Master Portal")
st.markdown("---")

# Premium Custom Cell-by-Cell Status Text Highlights
def style_premium_cells(val):
    clean_val = str(val).strip()
    if clean_val == 'Dispatched':
        return 'color: #10b981; font-weight: bold; font-size: 14px;' # Emerald Royal Green
    elif clean_val == 'Return':
        return 'color: #ef4444; font-weight: bold; font-size: 14px;' # Crimson Red
    elif clean_val == 'Pending':
        return 'color: #f59e0b; font-weight: bold; font-size: 14px;' # Cyber Amber Gold
    return ''

try:
    # 2. Read Data
    df = pd.read_csv('inventory.csv')
    st.sidebar.header("🎯 Control Center")

    # 3. SMART WAREHOUSE CONTROLLER
    LOCATION_COLUMN = 'Location' 
    if LOCATION_COLUMN in df.columns:
        df[LOCATION_COLUMN] = df[LOCATION_COLUMN].astype(str).str.strip()
        unique_locations = sorted(list(df[LOCATION_COLUMN].unique()))
        
        url_params = st.query_params
        
        if "warehouse" in url_params and url_params["warehouse"] in unique_locations and url_params.get("role") == "supervisor":
            target_warehouse = url_params["warehouse"]
            st.sidebar.info(f"📍 Location Locked: **{target_warehouse}**")
            df = df[df[LOCATION_COLUMN] == target_warehouse]
        else:
            master_options = ["All Locations"] + unique_locations
            selected_location = st.sidebar.selectbox("Select Warehouse Location (Master)", master_options)
            
            if selected_location != "All Locations":
                df = df[df[LOCATION_COLUMN] == selected_location]

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

    # 6. EXECUTIVE OPERATIONAL SUMMARY BANNER (Top of Dashboard)
    if STATUS_COLUMN in filtered_df.columns:
        # Compute calculations dynamically based on currently filtered dataset rows
        count_dispatched = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Dispatched'])
        count_pending = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Pending'])
        count_return = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Return'])
        
        st.markdown(f"""
            <div class="summary-box">
                <div class="summary-title">📈 Real-Time Logistics Summary Breakdown</div>
                <div class="summary-grid">
                    <div class="summary-item">🟢 Dispatched: <span style="color:#10b981; font-weight:700;">{count_dispatched}</span> items</div>
                    <div class="summary-item">🟡 Pending: <span style="color:#f59e0b; font-weight:700;">{count_pending}</span> entries</div>
                    <div class="summary-item">🔴 Returned: <span style="color:#ef4444; font-weight:700;">{count_return}</span> records</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 7. Premium KPI Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows Listed", f"{len(filtered_df):,}")
    with col2:
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else 0
        st.metric("Total Volume Quantity", f"{total_stock:,}")
    with col3:
        st.metric("Network Status", "Live Sync Operational")

    st.markdown("<br>### 📋 Live Logistics Manifest", unsafe_allow_html=True)

    # 8. Interactive Live Data Table with Applied Cell Text Colors
    if STATUS_COLUMN in filtered_df.columns and len(filtered_df) > 0:
        styled_df = filtered_df.style.map(style_premium_cells, subset=[STATUS_COLUMN])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ Core Database Error: 'inventory.csv' dataset was not detected.")
except Exception as e:
    st.error(f"An unexpected portal error occurred: {e}")
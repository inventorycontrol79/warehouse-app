import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os

# 1. Page Configuration & Premium Title Alignment
st.set_page_config(
    page_title="LOGIX // Warehouse Command Center", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Premium Dark-Mode Theme Architecture
st.markdown("""
    <style>
    /* Main Background Texture & Typography */
    .stApp { 
        background: radial-gradient(circle at 50% 50%, #111622 0%, #070a0f 100%);
        color: #f8fafc; 
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Header Customization */
    h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        letter-spacing: -1px;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 5px;
    }
    
    /* Sleek Top Banner Control */
    .premium-banner {
        background: linear-gradient(90deg, rgba(15,23,42,0.6) 0%, rgba(30,41,59,0.3) 100%);
        padding: 15px 25px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .banner-title { font-size: 13px; text-transform: uppercase; letter-spacing: 2px; color: #64748b; font-weight: 700; }
    
    /* Premium Metric Grid Display */
    div[data-testid="stMetric"] { 
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(10px);
        padding: 22px; 
        border-radius: 14px; 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 242, 254, 0.3);
    }
    div[data-testid="stMetricValue"] { font-size: 34px; font-weight: 800; color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; text-transform: uppercase; letter-spacing: 1.5px; font-size: 11px; font-weight: 600; }
    
    /* Custom Inline Status Badges */
    .status-badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .status-dispatched { background-color: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
    .status-pending { background-color: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.2); }
    .status-return { background-color: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
    
    /* Sidebar Overhaul */
    .stSidebar { background-color: #090d14 !important; border-right: 1px solid rgba(255,255,255,0.03) !important; }
    .stSidebar h2, .stSidebar h3 { color: #f1f5f9 !important; font-weight: 700; letter-spacing: -0.5px; }
    
    /* Clean Divider Lines */
    hr { border: 0; height: 1px; background: linear-gradient(to right, rgba(0, 242, 254, 0.4), transparent); margin: 25px 0px; }
    
    /* DataFrame View Adjustments */
    .stDataFrame { background: rgba(15, 23, 42, 0.2); border-radius: 12px; border: 1px solid rgba(255,255,255,0.03); }
    </style>
""", unsafe_allow_html=True)

# 3. Application Header Panel
st.title("LOGIX // Warehouse Command")
st.markdown("""
<div class="premium-banner">
    <div>
        <div class="banner-title">Operational Network</div>
        <div style="font-size: 15px; font-weight: 500; color: #e2e8f0;">Live Pipeline Streamlit Hub</div>
    </div>
    <div style="text-align: right;">
        <span class="status-badge status-dispatched">● WHATSAPP ENGINE ACTIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'

try:
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=['Location', 'Status', 'Date_Issued', 'Quantity', 'Last_4', 'DO_Number']).to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    # ------------------ SIDEBAR CONTROL PANEL ------------------
    st.sidebar.markdown("<h2 style='margin-bottom:-10px;'>CONTROL DESK</h2>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # 📤 Premium File Importer
    st.sidebar.subheader("Import ERP Manifest")
    uploaded_file = st.sidebar.file_uploader("Drop updated warehouse report file here", type=['csv', 'xlsx'], label_visibility="collapsed")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                uploaded_df = pd.read_excel(uploaded_file)
            else:
                uploaded_df = pd.read_csv(uploaded_file)
            
            uploaded_df.to_csv(CSV_FILE, index=False)
            st.sidebar.success("Manifest updated successfully.")
            df = pd.read_csv(CSV_FILE) 
            st.rerun()
        except Exception as upload_err:
            st.sidebar.error(f"Error processing import: {upload_err}")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # 📍 Adaptive Warehouse Location Lock / Filter
    LOCATION_COLUMN = 'Location' 
    if LOCATION_COLUMN in df.columns:
        df[LOCATION_COLUMN] = df[LOCATION_COLUMN].astype(str).str.strip()
        unique_locations = sorted(list(df[LOCATION_COLUMN].unique()))
        
        url_params = st.query_params
        
        if "warehouse" in url_params and url_params["warehouse"] in unique_locations and url_params.get("role") == "supervisor":
            target_warehouse = url_params["warehouse"]
            st.sidebar.info(f"📍 Station Locked:\n**{target_warehouse}**")
            df = df[df[LOCATION_COLUMN] == target_warehouse]
        else:
            master_options = ["All Terminals"] + unique_locations
            selected_location = st.sidebar.selectbox("Active Terminal Station", master_options)
            if selected_location != "All Terminals":
                df = df[df[LOCATION_COLUMN] == selected_location]

    # 📊 Status Filter
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
        existing_statuses = list(df[STATUS_COLUMN].unique())
        if 'Pending' in existing_statuses:
            existing_statuses.remove('Pending')
            status_options = ["All Metrics", "Pending Only"] + [f"{s} Only" for s in existing_statuses]
        else:
            status_options = ["All Metrics"] + [f"{s} Only" for s in existing_statuses]

        selected_status = st.sidebar.selectbox("Filter Status Stream", status_options)
        if "Pending Only" in selected_status:
            df = df[df[STATUS_COLUMN] == 'Pending']
        elif "All Metrics" not in selected_status:
            clean_stat = selected_status.replace(" Only", "")
            df = df[df[STATUS_COLUMN] == clean_stat]

    # 📅 Date Range Filter
    DATE_COLUMN = 'Date_Issued' 
    if DATE_COLUMN in df.columns:
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
        clean_dates = df[DATE_COLUMN].dropna()
        if not clean_dates.empty:
            st.sidebar.markdown("<br>", unsafe_allow_html=True)
            st.sidebar.subheader("Temporal Ranges")
            start_date = st.sidebar.date_input("From", min(clean_dates))
            end_date = st.sidebar.date_input("To", max(clean_dates))
            filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
        else:
            filtered_df = df
    else:
        filtered_df = df

    # ------------------ MAIN CONTENT GRID ------------------
    
    # 4. KPI Performance Metric Row
    if STATUS_COLUMN in filtered_df.columns:
        count_dispatched = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Dispatched'])
        count_pending = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Pending'])
        count_return = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Return'])
    else:
        count_dispatched, count_pending, count_return = 0, len(filtered_df), 0

    total_volume = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else 0

    # Clean 4-Column Layout
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Load Profile", f"{len(filtered_df):,} items")
    with m2:
        st.metric("Pending Queue", f"{count_pending:,} rows")
    with m3:
        st.metric("Dispatched Volume", f"{count_dispatched:,} rows")
    with m4:
        st.metric("Gross Units Moved", f"{total_volume:,} pcs")

    st.markdown("---")

    # 5. Live Manifest Data Grid Layout
    st.markdown("<h3 style='margin-bottom: 15px;'>Live Operations Pipeline</h3>", unsafe_allow_html=True)

    # Formatted Premium Cell Styling Logic
    def style_premium_cells(val):
        clean_val = str(val).strip()
        if clean_val == 'Dispatched': return 'color: #10b981; font-weight: 700; background-color: rgba(16, 185, 129, 0.05);'
        elif clean_val == 'Return': return 'color: #ef4444; font-weight: 700; background-color: rgba(239, 68, 68, 0.05);'
        elif clean_val == 'Pending': return 'color: #f59e0b; font-weight: 700; background-color: rgba(245, 158, 11, 0.05);'
        return ''

    # Output Data Grid View
    if len(filtered_df) > 0:
        if STATUS_COLUMN in filtered_df.columns:
            styled_df = filtered_df.style.map(style_premium_cells, subset=[STATUS_COLUMN])
            st.dataframe(styled_df, use_container_width=True, height=450)
        else:
            st.dataframe(filtered_df, use_container_width=True, height=450)
    else:
        st.info("No logs match the selected parameters in the current view.")

    # 📥 Clean Report Downloader Button
    if not filtered_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Logix Manifest Export')
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Download Executive Manifest Report (Excel)",
            data=buffer.getvalue(),
            file_name=f"LOGIX_Manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

except FileNotFoundError:
    st.error("🚨 System Manifest Missing: 'inventory.csv' could not be safely mapped to current engine variables.")
except Exception as e:
    st.error(f"Operational pipeline loop paused: {e}")
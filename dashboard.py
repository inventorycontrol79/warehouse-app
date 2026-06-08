import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import os
import re
import threading
import sys
from datetime import datetime
from io import BytesIO
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# Inject your custom workspace path to let Python discover the refactored bot module
BOT_DIR_PATH = "D:\\Afsal\\Whatsapp_bot"
if BOT_DIR_PATH not in sys.path:
    sys.path.append(BOT_DIR_PATH)

try:
    import bot  # Imports your background WhatsApp radar loop dynamically
except ImportError:
    st.error(f"❌ Could not import 'bot.py'. Please confirm that bot.py exists in '{BOT_DIR_PATH}'")

# 1. Page Configuration & Professional UI Styles
st.set_page_config(
    page_title="Warehouse Verification Control",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional UI CSS customization
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { font-family: 'Segoe UI', Helvetica, sans-serif; font-weight: 600; color: #2c3e50; }
    div[data-testid="stMetricValue"] { font-size: 28px !important; font-weight: 700 !important; color: #1e293b !important; }
    div[data-testid="stMetricLabel"] { font-size: 14px !important; font-weight: 500 !important; color: #64748b !important; }
    .custom-hr { border: 0; height: 1px; background: #e2e8f0; margin: 1.5rem 0; }
    .stCheckbox { margin-top: -10px; }
    </style>
""", unsafe_allow_html=True)

CSV_FILE_PATH = "D:\\Afsal\\Whatsapp_bot\\inventory.csv"
ARCHIVE_FILE_PATH = "D:\\Afsal\\Whatsapp_bot\\inventory_archive.csv"

def load_warehouse_data():
    for attempt in range(3):
        try:
            df = pd.read_csv(CSV_FILE_PATH)
            df.columns = df.columns.str.strip()
            
            if 'Godown' in df.columns:
                df = df.rename(columns={'Godown': 'Warehouse_Name'})
            elif 'Warehouse Name' in df.columns:
                df = df.rename(columns={'Warehouse Name': 'Warehouse_Name'})
                
            if 'Remarks' not in df.columns:
                df['Remarks'] = "Standard Delivery"
                
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()
                
            df['Remarks'] = df['Remarks'].replace(['nan', 'None', 'NaN', ''], 'Standard Delivery')
            
            if 'Date_Issued' in df.columns:
                df['Date_Issued_Parsed'] = pd.to_datetime(df['Date_Issued'], errors='coerce')
            else:
                df['Date_Issued_Parsed'] = pd.to_datetime(time.strftime('%Y-%m-%d'), errors='coerce')
                
            return df
        except PermissionError:
            time.sleep(0.5)
        except FileNotFoundError:
            st.error(f"❌ File not found at: {CSV_FILE_PATH}")
            st.stop()
    st.error("🔄 Inventory database is currently busy.")
    st.stop()

df_raw = load_warehouse_data()

status_colors = {
    'Dispatched': '#2ecc71',
    'Pending': '#f1c40f',
    'Return': '#e74c3c'
}

# Intercept URL parameters for branch supervisor specific console views
query_params = st.query_params
assigned_warehouse = query_params.get("view", None)

# Shared column formatting configuration map
grid_config = {
    "DO_Number": st.column_config.TextColumn("Delivery Order Number", disabled=True),
    "Last_4": st.column_config.TextColumn("Ending Sequence", disabled=True),
    "Created_By": st.column_config.TextColumn("Document Creator Reference", disabled=True),
    "Date_Issued": st.column_config.TextColumn("Date Registered", disabled=True),
    "Warehouse_Name": st.column_config.TextColumn("Operational Hub", disabled=True),
    "Status": st.column_config.SelectboxColumn("Status", options=["Pending", "Dispatched", "Return"], required=True),
    "Remarks": st.column_config.TextColumn("Remarks / Operational Comments", max_chars=250, disabled=False)
}

# Inline row text color highlighting engine for Status entries
def color_status_text(val):
    clean_val = str(val).strip().lower()
    if clean_val == 'dispatched': return 'color: #2ecc71; font-weight: bold;'
    elif clean_val == 'pending': return 'color: #f1c40f; font-weight: bold;'
    elif 'return' in clean_val: return 'color: #e74c3c; font-weight: bold;'
    return ''

if assigned_warehouse:
    # -----------------------------------------------------------------
    # MODE A: SUPERVISOR READ-ONLY CONSOLE
    # -----------------------------------------------------------------
    st.title(f"📋 {assigned_warehouse} — Live Monitor")
    st.caption("Real-time tracking manifest for open pending items and finished dispatches.")
    st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)
    
    if 'Warehouse_Name' in df_raw.columns:
        df_sup = df_raw[df_raw['Warehouse_Name'].str.lower() == assigned_warehouse.lower()].copy()
    else:
        df_sup = pd.DataFrame()
        st.error("Configuration Column Error: Warehouse_Name not detected in data matrix.")
        
    if df_sup.empty:
        st.warning(f"No active inventory orders currently cataloged for node: '{assigned_warehouse}'")
    else:
        t_total = len(df_sup)
        t_disp = len(df_sup[df_sup['Status'].str.lower() == 'dispatched'])
        t_pend = len(df_sup[df_sup['Status'].str.lower() == 'pending'])
        t_ret = len(df_sup[df_sup['Status'].str.lower().str.contains('return')])
        
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Your Total Orders", t_total)
        sm2.metric("✅ Dispatched Items", t_disp)
        sm3.metric("⏳ Outstanding Pending", t_pend)
        sm4.metric("🔄 Returns Registered", t_ret)
        
        st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)
        
        st.subheader("Your Delivery Order Queue Status")
        if 'Date_Issued_Parsed' in df_sup.columns:
            df_sup = df_sup.drop(columns=['Date_Issued_Parsed'])
            
        readonly_config = {k: st.column_config.TextColumn(v.label, disabled=True) for k, v in grid_config.items()}
        active_config = {k: v for k, v in readonly_config.items() if k in df_sup.columns}
        
        styled_sup = df_sup.style.map(color_status_text, subset=['Status'] if 'Status' in df_sup.columns else [])
        st.data_editor(styled_sup, use_container_width=True, column_config=active_config, hide_index=True, key="sup_grid")
        
    st.stop()


# -----------------------------------------------------------------
# MODE B: MASTER ADMIN DASHBOARD
# -----------------------------------------------------------------
st.sidebar.title("🛠️ Control Center")

# --- CONCURRENT WHATSAPP BOT SERVICE CONTROLLER ---
st.sidebar.markdown("### 🤖 WhatsApp Automation Service")

if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None
if "bot_stop_event" not in st.session_state:
    st.session_state.bot_stop_event = None

if st.session_state.bot_thread is None or not st.session_state.bot_thread.is_alive():
    if st.sidebar.button("▶️ Start WhatsApp Automation Bot", type="primary", use_container_width=True):
        st.session_state.bot_stop_event = threading.Event()
        st.session_state.bot_thread = threading.Thread(
            target=bot.background_whatsapp_radar_loop, 
            args=(st.session_state.bot_stop_event,),
            daemon=True
        )
        st.session_state.bot_thread.start()
        st.sidebar.success("🚀 Initializing thread. Launching Chrome profile container...")
        time.sleep(1)
        st.rerun()
else:
    st.sidebar.markdown("🟢 **Status:** `Bot Radar Listening Live...`")
    if st.sidebar.button("🛑 Stop WhatsApp Automation Bot", type="secondary", use_container_width=True):
        st.session_state.bot_stop_event.set()
        st.session_state.bot_thread = None
        st.sidebar.warning("🛑 Termination pipeline triggered. Parking automation contexts...")
        time.sleep(1)
        st.rerun()

st.sidebar.markdown("---")

if os.path.exists(CSV_FILE_PATH):
    last_mod_time = os.path.getmtime(CSV_FILE_PATH)
    formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_mod_time))
    st.sidebar.caption(f"💾 **Bot Sync Last Mod:** `{formatted_time}`")

# --- DYNAMIC INTELLIGENT ERP FILE UPLOADER ---
st.sidebar.markdown("### 📤 Update Master Inventory")
uploaded_file = st.sidebar.file_uploader("Upload Raw ERP Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Step 1: Read the Excel file completely raw
        df_raw_excel = pd.read_excel(uploaded_file, header=None)
        
        # Step 2: Scan rows to dynamically find where the true column headers sit
        header_row_index = None
        for idx, row in df_raw_excel.iterrows():
            row_values = row.astype(str).str.strip().tolist()
            if any("Voucher No." in val for val in row_values):
                header_row_index = idx
                break
                
        if header_row_index is None:
            st.sidebar.error("❌ Could not locate the header row (looking for 'Voucher No.') in this document.")
        else:
            # Step 3: Re-slice data frame starting precisely from the header row down
            df_erp = pd.read_excel(uploaded_file, skiprows=header_row_index)
            df_erp.columns = df_erp.columns.str.strip()
            
            # Verify the primary columns are present EXACTLY as they come from the raw ERP export
            required_cols = ['Voucher No.', 'Date', 'Customer Name', 'Created user']
            if not all(col in df_erp.columns for col in required_cols):
                st.sidebar.error("❌ Layout Mismatch! Expected: 'Voucher No.', 'Date', 'Customer Name', and 'Created user'.")
            else:
                # Step 4: Clean and purge the bottom "Grand Total" rows safely
                df_erp['Voucher No.'] = df_erp['Voucher No.'].astype(str).str.strip()
                df_erp = df_erp[
                    (~df_erp['Voucher No.'].str.contains('Total', case=False, na=False)) & 
                    (df_erp['Voucher No.'] != 'nan') & 
                    (df_erp['Voucher No.'] != '')
                ]
                
                # Step 5: Remap original ERP names to clean system layouts 
                # Changes 'Customer Name' (manually edited to hold location) into internal 'Godown' column
                mapping_dict = {
                    'Voucher No.': 'Voucher No',
                    'Customer Name': 'Godown',
                    'Created user': 'Created By'
                }
                df_erp = df_erp.rename(columns=mapping_dict)
                
                # Step 6: Package data frame straight to dashboard metrics format
                df_cleaned = pd.DataFrame()
                df_cleaned['DO_Number'] = df_erp['Voucher No']
                df_cleaned['Last_4'] = df_cleaned['DO_Number'].str[-4:]
                df_cleaned['Date_Issued'] = pd.to_datetime(df_erp['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                df_cleaned['Warehouse_Name'] = df_erp['Godown'].astype(str).str.strip()
                df_cleaned['Created_By'] = df_erp['Created By'].astype(str).str.strip()
                df_cleaned['Status'] = 'Pending'
                df_cleaned['Remarks'] = "Standard Delivery"
                
                # Deduplicate entries safely
                df_cleaned = df_cleaned.dropna(subset=['DO_Number'])
                df_cleaned = df_cleaned.drop_duplicates(subset=['DO_Number'], keep='first')
                
                # Read and join with your ongoing tracking file history
                current_master = pd.DataFrame()
                if os.path.exists(CSV_FILE_PATH):
                    for attempt in range(3):
                        try:
                            current_master = pd.read_csv(CSV_FILE_PATH)
                            current_master.columns = current_master.columns.str.strip()
                            current_master['DO_Number'] = current_master['DO_Number'].astype(str).str.strip()
                            break
                        except PermissionError:
                            time.sleep(0.5)
                
                if not current_master.empty:
                    new_records = df_cleaned[~df_cleaned['DO_Number'].isin(current_master['DO_Number'])]
                else:
                    new_records = df_cleaned

                if not new_records.empty:
                    if 'Remarks' not in current_master.columns and not current_master.empty:
                        current_master['Remarks'] = "Standard Delivery"
                    
                    updated_master = pd.concat([current_master, new_records], ignore_index=True)
                    
                    for attempt in range(3):
                        try:
                            updated_master.to_csv(CSV_FILE_PATH, index=False)
                            st.sidebar.success(f"✅ Successfully processed {len(new_records)} new unique orders!")
                            time.sleep(1)
                            st.rerun()
                            break
                        except PermissionError:
                            time.sleep(0.5)
                else:
                    st.sidebar.info("ℹ️ Upload checked. No new unique entries discovered.")
                    
    except Exception as e:
        st.sidebar.error(f"⚠️ Parsing engine error: {e}")

st.sidebar.markdown("### 🗄️ Database Optimization")
if st.sidebar.button("📦 Archive Completed Orders"):
    try:
        current_data = pd.read_csv(CSV_FILE_PATH)
        current_data.columns = current_data.columns.str.strip()
        
        dispatched_mask = current_data['Status'].astype(str).str.strip().str.lower() == 'dispatched'
        to_archive = current_data[dispatched_mask]
        to_keep = current_data[~dispatched_mask]
        
        if not to_archive.empty:
            if os.path.exists(ARCHIVE_FILE_PATH):
                archive_df = pd.read_csv(ARCHIVE_FILE_PATH)
                archive_df = pd.concat([archive_df, to_archive], ignore_index=True)
            else:
                archive_df = to_archive
                
            archive_df.to_csv(ARCHIVE_FILE_PATH, index=False)
            to_keep.to_csv(CSV_FILE_PATH, index=False)
            st.sidebar.success(f"🎉 Archived {len(to_archive)} records!")
            time.sleep(1.5)
            st.rerun()
        else:
            st.sidebar.info("ℹ️ No orders ready to archive.")
    except Exception as e:
        st.sidebar.error(f"⚠️ Archive processing error: {e}")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown("### 🔍 Filter Dashboard Views")
search_query = st.sidebar.text_input("Global Search", "", placeholder="Search DO # or Creator...")

st.sidebar.markdown("#### 📅 Timeline Filter Settings")
date_filter_mode = st.sidebar.radio("Select Date Filter Mode", ["All Data", "Month-wise", "Specific Period Range"])

df_date_filtered = df_raw.copy()

if date_filter_mode == "Month-wise":
    df_valid_dates = df_raw[df_raw['Date_Issued_Parsed'].notna()].copy()
    if not df_valid_dates.empty:
        df_valid_dates['Year_Month'] = df_valid_dates['Date_Issued_Parsed'].dt.strftime('%Y-%m')
        available_months = sorted(df_valid_dates['Year_Month'].unique().tolist(), reverse=True)
        selected_month = st.sidebar.selectbox("Choose Target Month", options=available_months)
        df_date_filtered = df_raw[(df_raw['Date_Issued_Parsed'].notna()) & (df_raw['Date_Issued_Parsed'].dt.strftime('%Y-%m') == selected_month)]

elif date_filter_mode == "Specific Period Range":
    min_date = df_raw['Date_Issued_Parsed'].min() if df_raw['Date_Issued_Parsed'].notna().any() else None
    max_date = df_raw['Date_Issued_Parsed'].max() if df_raw['Date_Issued_Parsed'].notna().any() else None
    if min_date and max_date:
        selected_range = st.sidebar.date_input("Select Date Window", value=(min_date.date(), max_date.date()), min_value=min_date.date(), max_value=max_date.date())
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_bound, end_bound = selected_range
            df_date_filtered = df_raw[(df_raw['Date_Issued_Parsed'].notna()) & (df_raw['Date_Issued_Parsed'].dt.date >= start_bound) & (df_raw['Date_Issued_Parsed'].dt.date <= end_bound)]

all_warehouses = sorted(df_date_filtered['Warehouse_Name'].unique().tolist()) if 'Warehouse_Name' in df_date_filtered.columns else []
selected_warehouses = st.sidebar.multiselect("Select Warehouses", options=all_warehouses, default=all_warehouses)

all_statuses = sorted(df_date_filtered['Status'].unique().tolist()) if 'Status' in df_date_filtered.columns else []
selected_statuses = st.sidebar.multiselect("Filter Statuses", options=all_statuses, default=all_statuses)

if 'Warehouse_Name' in df_date_filtered.columns:
    df_filtered = df_date_filtered[(df_date_filtered['Warehouse_Name'].isin(selected_warehouses)) & (df_date_filtered['Status'].isin(selected_statuses))].copy()
else:
    df_filtered = df_date_filtered[(df_date_filtered['Status'].isin(selected_statuses))].copy()

if search_query:
    mask = df_filtered.drop(columns=['Date_Issued_Parsed'], errors='ignore').astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
    df_filtered = df_filtered[mask]

st.sidebar.markdown("#### ↕️ Arrange Records")
sort_options = [col for col in ["Date_Issued", "DO_Number", "Status", "Warehouse_Name"] if col in df_filtered.columns]
if sort_options:
    sort_metric = st.sidebar.selectbox("Sort Order Column", options=sort_options)
    sort_asc = st.sidebar.radio("Direction", ["Ascending", "Descending"]) == "Ascending"
    df_filtered = df_filtered.sort_values(by=sort_metric, ascending=sort_asc)

st.title("📦 Logistics Verification & Dispatch Control (Admin)")
st.caption("Master administration dashboard console with raw file updates and multi-site configuration controls.")
st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)

total_orders_calc = len(df_filtered)
dispatched_count = len(df_filtered[df_filtered['Status'].str.lower() == 'dispatched']) if 'Status' in df_filtered.columns else 0
pending_count = len(df_filtered[df_filtered['Status'].str.lower() == 'pending']) if 'Status' in df_filtered.columns else 0
return_count = len(df_filtered[df_filtered['Status'].str.lower().str.contains('return')]) if 'Status' in df_filtered.columns else 0
efficiency_rate = (dispatched_count / total_orders_calc * 100) if total_orders_calc > 0 else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Tracked Load", total_orders_calc)
m2.metric("✅ Dispatched Orders", dispatched_count)
with m3:
    st.metric("⏳ Pending Lineup", pending_count)
    focus_actionable = st.checkbox("⚠️ Focus Action Items")
m4.metric("🔄 Marked Returns", return_count)

if focus_actionable and 'Status' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['Status'].str.lower() != 'dispatched']

if 'Date_Issued_Parsed' in df_filtered.columns:
    df_filtered = df_filtered.drop(columns=['Date_Issued_Parsed'])

st.markdown(f"**Current Operational Automation Efficiency:** `{efficiency_rate:.1f}%`")
st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns([1, 2])
with col_chart1:
    st.subheader("Milestone Distribution")
    if len(df_filtered) > 0 and 'Status' in df_filtered.columns:
        status_counts = df_filtered['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_pie = px.pie(status_counts, values='Count', names='Status', hole=0.4, color='Status', color_discrete_map=status_colors)
        fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=True, height=280)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No active matching entries in scope to chart.")

with col_chart2:
    st.subheader("Regional Hub Outputs")
    if len(df_filtered) > 0 and 'Warehouse_Name' in df_filtered.columns:
        fig_bar = px.bar(df_filtered, x='Warehouse_Name', color='Status' if 'Status' in df_filtered.columns else None, barmode='group', color_discrete_map=status_colors)
        fig_bar.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=280, xaxis_title="Warehouse Location", yaxis_title="Orders")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("⚠️ No warehouse records found.")

st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)

# --- MASTER ACTION LOG DATA GRID ---
st.subheader("📋 Active Operations Log")
if 'Remarks' in df_filtered.columns:
    df_filtered['Remarks'] = df_filtered['Remarks'].fillna('Standard Delivery')

if df_filtered.empty:
    st.info("No orders found matching the filter layout criteria.")
else:
    st.caption("💡 **Data Editor:** Double-click cells within 'Status' or 'Remarks' below to modify records. The status column text highlights automatically based on changes.")
    
    active_config = {k: v for k, v in grid_config.items() if k in df_filtered.columns}
    styled_admin_df = df_filtered.style.map(color_status_text, subset=['Status'] if 'Status' in df_filtered.columns else [])

    edited_df = st.data_editor(
        styled_admin_df, 
        use_container_width=True, 
        column_config=active_config, 
        hide_index=True, 
        key="operations_grid"
    )

    if st.button("💾 Save Manual Changes", type="primary"):
        for attempt in range(3):
            try:
                master_df = pd.read_csv(CSV_FILE_PATH)
                master_df.columns = master_df.columns.str.strip()
                if 'Godown' in master_df.columns:
                    master_df = master_df.rename(columns={'Godown': 'Warehouse_Name'})
                elif 'Warehouse Name' in master_df.columns:
                    master_df = master_df.rename(columns={'Warehouse Name': 'Warehouse_Name'})
                
                if 'Remarks' not in master_df.columns:
                    master_df['Remarks'] = "Standard Delivery"
                
                for idx, row in edited_df.iterrows():
                    do_num = row['DO_Number']
                    new_status = row['Status']
                    new_remarks = row['Remarks']
                    mask = master_df['DO_Number'].astype(str).str.strip() == str(do_num).strip()
                    if 'Status' in master_df.columns: master_df.loc[mask, 'Status'] = new_status
                    if 'Remarks' in master_df.columns: master_df.loc[mask, 'Remarks'] = new_remarks
                    
                master_df.to_csv(CSV_FILE_PATH, index=False)
                st.success("🎉 Changes updated successfully!")
                time.sleep(1)
                st.rerun()
                break
            except PermissionError:
                time.sleep(0.5)

st.markdown('<div class="custom-hr"></div>', unsafe_allow_html=True)

# --- PROFESSIONAL EXCEL EXPORTER MANIFEST CARD ---
st.markdown("### 📥 Professional Data Extraction")
HEADER_MAPPING = {
    'DO_Number': 'Delivery Order Reference', 'Last_4': 'Trailing Match Tag',
    'Created_By': 'Document Creator Reference', 'Status': 'Operational Milestone Status',
    'Date_Issued': 'Manifest Creation Date', 'Warehouse_Name': 'Dispatched Hub Node',
    'Remarks': 'Operational Notes & Exceptions'
}

def convert_df_to_excel(df_to_export):
    output = BytesIO()
    columns_to_keep = [col for col in df_to_export.columns if col in HEADER_MAPPING.keys()]
    final_df = df_to_export[columns_to_keep].rename(columns=HEADER_MAPPING)
    t_orders = len(df_to_export)
    t_dispatched = len(df_to_export[df_to_export['Status'].str.lower() == 'dispatched']) if 'Status' in df_to_export.columns else 0
    t_pending = len(df_to_export[df_to_export['Status'].str.lower() == 'pending']) if 'Status' in df_to_export.columns else 0
    t_returns = len(df_to_export[df_to_export['Status'].str.lower().str.contains('return')]) if 'Status' in df_to_export.columns else 0
    t_efficiency = (t_dispatched / t_orders) if t_orders > 0 else 0.0

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        SHEET_NAME = 'Delivery Dispatch status'
        final_df.to_excel(writer, index=False, sheet_name=SHEET_NAME, startrow=7)
        worksheet = writer.sheets[SHEET_NAME]
        
        font_title = Font(name='Segoe UI', size=12, bold=True, color='1F3A52')
        font_kpi_label = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
        font_kpi_val = Font(name='Segoe UI', size=11, bold=True, color='1F3A52')
        header_font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
        data_font = Font(name='Segoe UI', size=10, color='2C3E50')
        
        fill_kpi_header = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        fill_kpi_card = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
        header_fill = PatternFill(start_color="1F3A52", end_color="1F3A52", fill_type="solid")
        thin_border_side = Side(style='thin', color='D1D5DB')
        grid_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
        
        worksheet['A1'] = "WAREHOUSE DISPATCH PERFORMANCE SUMMARY"
        worksheet['A1'].font = font_title
        
        kpis = [
            ("Total Tracked Orders", f"{t_orders} Pcs", "A", "B"),
            ("Dispatched Orders", f"{t_dispatched} Pcs", "C", "D"),
            ("Pending Orders", f"{t_pending} Pcs", "E", "F"),
            ("Marked Returns", f"{t_returns} Pcs", "G", "H")
        ]
        
        for label, val, start_col, end_col in kpis:
            worksheet.merge_cells(f"{start_col}3:{end_col}3")
            worksheet.merge_cells(f"{start_col}4:{end_col}4")
            worksheet[f"{start_col}3"].value = label
            worksheet[f"{start_col}3"].font = font_kpi_label
            worksheet[f"{start_col}3"].fill = fill_kpi_header
            worksheet[f"{start_col}3"].alignment = Alignment(horizontal="center", vertical="center")
            worksheet[f"{start_col}4"].value = val
            worksheet[f"{start_col}4"].font = font_kpi_val
            worksheet[f"{start_col}4"].fill = fill_kpi_card
            worksheet[f"{start_col}4"].alignment = Alignment(horizontal="center", vertical="center")
            for r in [3, 4]:
                worksheet[f"{start_col}{r}"].border = grid_border
                worksheet[f"{end_col}{r}"].border = grid_border

        worksheet.merge_cells("A5:D5")
        worksheet["A5"] = f"Current Operational Automation Efficiency:  {t_efficiency:.1%}"
        worksheet["A5"].font = Font(name='Segoe UI', size=10, bold=True, color='2C3E50')

        worksheet.row_dimensions[8].height = 26
        for cell in worksheet[8]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        fill_dispatched = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
        fill_pending = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        fill_return = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

        mapped_status_col_name = HEADER_MAPPING.get('Status', 'Status')
        status_col_idx = final_df.columns.get_loc(mapped_status_col_name) + 1 if mapped_status_col_name in final_df.columns else 1

        for row_idx in range(9, worksheet.max_row + 1):
            worksheet.row_dimensions[row_idx].height = 20
            status_value = str(worksheet.cell(row=row_idx, column=status_col_idx).value).strip().lower()
            current_fill = fill_dispatched if status_value == 'dispatched' else (fill_pending if status_value == 'pending' else (fill_return if 'return' in status_value else None))

            for col_idx in range(1, worksheet.max_column + 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = grid_border
                cell.alignment = Alignment(horizontal="center" if col_idx in [status_col_idx, 1, 2, 5] else "left", vertical="center")
                if current_fill: cell.fill = current_fill
        
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            worksheet.column_dimensions[col[0].column_letter].width = max(max_len + 5, 16)
            
    return output.getvalue()

if not df_filtered.empty:
    excel_data = convert_df_to_excel(df_filtered)
    st.download_button(label="📥 Download Excel Dispatch Manifest", data=excel_data, file_name="Warehouse_Manifest_Extract.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
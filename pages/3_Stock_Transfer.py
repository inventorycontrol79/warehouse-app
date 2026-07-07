import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import numpy as np

# =====================================================
# 1. PAGE SETUP & SECURITY ASSIGNMENT
# =====================================================
st.set_page_config(page_title="SABIN PLASTIC // Stock Transfer Hub", layout="wide")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Synchronize administrative privileges
url_params = st.query_params
if url_params.get("key", "") == "sabin_inventory":
    st.session_state.is_admin = True

is_admin = st.session_state.is_admin

# Premium High-Contrast Dark Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    
    /* Main App Background */
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Force Entire Sidebar Content & Navigation Links to White */
    [data-testid="stSidebar"] div, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] a { 
        color: #FFFFFF !important; 
    }
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B !important; }
    
    /* Premium Sidebar Component Tweaks */
    [data-testid="stExpander"] { background-color: #111827 !important; border: 1px solid #1E293B !important; border-radius: 8px; }
    [data-testid="stExpander"] summary { color: #FFFFFF !important; }
    [data-testid="stFileUploader"] section { background-color: #111827 !important; border: 1px dashed #38BDF8 !important; }
    
    /* Typography and Operational Interface Styling */
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #FFFFFF !important; font-weight: 600 !important; }
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 11px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    .card-box { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 22px; margin-bottom: 20px; }
    .advice-card { background-color: #151F32; border-left: 4px solid #38BDF8; border-radius: 6px; padding: 16px; margin-bottom: 12px; border-top: 1px solid #1E293B; border-right: 1px solid #1E293B; border-bottom: 1px solid #1E293B; }
    .critical-badge { color: #F87171 !important; font-weight: 800; background-color: rgba(239, 68, 68, 0.15); padding: 4px 8px; border-radius: 4px; }
    .surplus-badge { color: #34D399 !important; font-weight: 800; background-color: rgba(52, 211, 153, 0.15); padding: 4px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# Shared Custom Brand Layout Header
st.markdown("""
    <div class='premium-header'>
        <div class='sabin-logo'>SABIN <span>PLASTIC</span></div>
        <div class='sabin-sub'>Multi-Warehouse Stock Transfer & Advisor System</div>
    </div>
""", unsafe_allow_html=True)

# =====================================================
# 2. SECURE GOOGLE CLOUD STORAGE CONNECTION
# =====================================================
def get_google_client():
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Google Cloud Security Link Failed: {e}")
        return None

@st.cache_data(ttl=300)
def pull_master_stock_data():
    gc = get_google_client()
    if not gc:
        return pd.DataFrame(), None
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        ws = sh.get_worksheet(3) # Tab Index 3: Stock
        data = ws.get_all_records()
        return pd.DataFrame(data), ws
    except Exception as e:
        st.error(f"🚨 Error Fetching Master Stock sheet: {e}")
        return pd.DataFrame(), None

df_stock, ws_stock_raw = pull_master_stock_data()

# Warehouse Mapping Config Dictionary to match Focus ERP names
WH_MAP = {
    "Sharjah Trading SP": "Stock_Sharjah",
    "Al Quoz Trading SP": "Stock_Al_Quoz",
    "DIP Warehouse SP": "Stock_DIP",
    "Abu Dhabi Depot SP": "Stock_Abu_Dhabi"
}

# The Exact Global Column Structure
TARGET_COLUMNS = [
    "Item_Code", "Item_Name", "Product_Category", "Current_Stock",
    "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi",
    "ABC_Category", "Avg_Daily_Sales", "Last_Sold_Date", "Days_of_Coverage"
]

# =====================================================
# 3. WORKSPACE PORTAL A: ONE-TIME INITIALIZATION (ADMIN)
# =====================================================
if is_admin:
    with st.sidebar.expander("🛠️ SYSTEM MASTER INITIALIZATION"):
        st.markdown("<small>Use this to upload a baseline if setting physical stock for the first time.</small>", unsafe_allow_html=True)
        init_file = st.file_uploader("Upload Master Stock Balance File", type=["xlsx", "csv"], key="init_uploader")
        
        if init_file is not None and st.button("🚀 BULK OVERWRITE STOCK BASELINE"):
            try:
                df_init = pd.read_excel(init_file) if init_file.name.endswith("xlsx") else pd.read_csv(init_file)
                df_init.columns = [str(c).strip() for c in df_init.columns]
                
                req = ["Item_Code", "Item_Name", "Stock_Sharjah", "Stock_Al_Quoz"]
                if all(c in df_init.columns for c in req):
                    gc = get_google_client()
                    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
                    ws_to_init = sh.get_worksheet(3)
                    
                    for col in TARGET_COLUMNS:
                        if col not in df_init.columns:
                            df_init[col] = "" 
                    
                    df_to_upload = df_init[TARGET_COLUMNS].copy()
                    
                    def serialize_cell(val):
                        if pd.isna(val) or val is None or str(val).strip().lower() in ['nan', 'nat', 'inf', '-inf']:
                            return ""
                        return str(val).strip()
                    
                    clean_rows = df_to_upload.map(serialize_cell).values.tolist()
                    
                    ws_to_init.clear()
                    ws_to_init.append_rows([TARGET_COLUMNS] + clean_rows)
                    
                    st.success("🎉 Master database structure initialized successfully with zero compliance errors!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Column structure mismatch. Ensure warehouse name suffixes are present.")
            except Exception as e:
                st.error(f"Initialization Failed: {e}")

# =====================================================
# 4. WORKSPACE PORTAL B: DAILY FOCUS ERP LEDGER INGESTION
# =====================================================
st.header("📥 Ingest Daily Focus ERP Stock Ledger")
st.markdown("Drop yesterday's audited stock ledger here. The system will auto-extract **SRTS** internal movements and update regional balances. **Current_Stock (Global)** remains untouched.")

if not is_admin:
    st.warning("🔒 Device write lock is active. Please use your authenticated dashboard link to process files.")
else:
    uploaded_ledger = st.file_uploader("Select Focus ERP Stock Ledger Export File", type=["xlsx", "csv"])
    
    if uploaded_ledger is not None:
        if st.button("⚡ EXECUTE DOUBLE-ENTRY TRANSFER AUTOMATION", use_container_width=True):
            try:
                # 1. Read the file without skipping rows initially to find the correct headers dynamically
                if uploaded_ledger.name.endswith(".csv"):
                    df_raw_check = pd.read_csv(uploaded_ledger, header=None)
                else:
                    df_raw_check = pd.read_excel(uploaded_ledger, header=None)
                
                # Find the row index that contains our required ERP tracking keys
                header_row_idx = 0
                for idx, row_data in df_raw_check.iterrows():
                    row_strs = [str(cell).strip().lower() for cell in row_data.values]
                    if any("voucher" in s for s in row_strs) and any("code" in s for s in row_strs):
                        header_row_idx = idx
                        break
                
                # 2. Reload the data using the dynamically discovered header position
                if uploaded_ledger.name.endswith(".csv"):
                    raw_ledger = pd.read_csv(uploaded_ledger, skiprows=header_row_idx)
                else:
                    raw_ledger = pd.read_excel(uploaded_ledger, skiprows=header_row_idx)
                
                # Standardize column naming rules
                raw_ledger.columns = [str(c).strip() for c in raw_ledger.columns]
                
                # Flexible match: Look for 'Voucher' or any header starting with 'Voucher'
                voucher_col = None
                for col in raw_ledger.columns:
                    if col.lower().startswith("voucher"):
                        voucher_col = col
                        break
                
                if not voucher_col:
                    st.error("❌ Critical Structure Failure: Could not find a 'Voucher' column anywhere in the file rows.")
                    st.stop()
                
                # Process the data using the discovered column
                srts_data = raw_ledger[raw_ledger[voucher_col].astype(str).str.startswith("SRTS")].copy()
                
                if srts_data.empty:
                    st.warning("ℹ️ No active SRTS internal transfer vouchers recorded inside the uploaded ledger.")
                else:
                    gc = get_google_client()
                    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
                    ws_stock = sh.get_worksheet(3)
                    ws_log = sh.get_worksheet(4) # Tab Index 4: Logs
                    
                    current_stock_df = pd.DataFrame(ws_stock.get_all_records())
                    
                    # Ensure hybrid columns exist to prevent KeyError
                    for col in ["Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi"]:
                        if col not in current_stock_df.columns:
                            current_stock_df[col] = 0
                            
                    srts_data["Received Quantity"] = pd.to_numeric(srts_data["Received Quantity"], errors="coerce").fillna(0)
                    srts_data["Issued Quantity"] = pd.to_numeric(srts_data["Issued Quantity"], errors="coerce").fillna(0)
                    
                    processed_transfers = 0
                    
                    for voucher_no, group in srts_data.groupby(voucher_col):
                        for _, row in group.iterrows():
                            item_sku = str(row["Code"]).strip()
                            wh_raw = str(row["Warehouse Name"]).strip()
                            
                            matched_wh_column = None
                            for erp_name, sheet_col in WH_MAP.items():
                                if erp_name.lower() in wh_raw.lower():
                                    matched_wh_column = sheet_col
                                    break
                            
                            if not matched_wh_column:
                                continue 
                                
                            issued_qty = float(row["Issued Quantity"])
                            received_qty = float(row["Received Quantity"])
                            
                            if item_sku in current_stock_df["Item_Code"].values:
                                if issued_qty > 0: 
                                    current_stock_df.loc[current_stock_df["Item_Code"] == item_sku, matched_wh_column] -= issued_qty
                                    ws_log.append_row([str(row["Date"]), str(voucher_no), f"Transfer Out ({wh_raw})", -issued_qty, item_sku, "SYSTEM_AUTO_HUB"])
                                if received_qty > 0: 
                                    current_stock_df.loc[current_stock_df["Item_Code"] == item_sku, matched_wh_column] += received_qty
                                    ws_log.append_row([str(row["Date"]), str(voucher_no), f"Transfer In ({wh_raw})", received_qty, item_sku, "SYSTEM_AUTO_HUB"])
                                processed_transfers += 1
                    
                    if processed_transfers > 0:
                        ws_stock.clear()
                        ws_stock.append_rows([current_stock_df.columns.tolist()] + current_stock_df.fillna("").astype(str).values.tolist())
                        st.success(f"🎉 Successfully automated {processed_transfers} double-entry transfer changes across cloud warehouse ledgers!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.info("No matching warehouse location parameters were found to match.")
            except Exception as e:
                st.error(f"🚨 Critical Failure Parsing Ledger File: {e}")

# =====================================================
# 5. WORKSPACE PORTAL C: THE FORESIGHT DEMAND ADVISOR
# =====================================================
st.header("🧠 Intelligent Supply Redistribution Advisor")
st.markdown("Evaluates global velocity against regional stock distributions to flag required transfers.")

if df_stock.empty:
    st.info("ℹ️ Master warehouse balance tables are currently uninitialized or processing stock sync values.")
else:
    # --- SAFETY VALVE: Helper to clean numbers ---
    def clean_float(value):
        try:
            return float(value) if str(value).strip() != "" else 0.0
        except (ValueError, TypeError):
            return 0.0
    # ---------------------------------------------

    # Ensure required columns exist
    for k in ["Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi", "Avg_Daily_Sales"]:
        if k not in df_stock.columns:
            df_stock[k] = 0

    # 🔍 GLOBAL SEARCH ROUTINE (Visible to all users)
    search_query = st.text_input("🔍 Search Matrix or Routes by SKU / Item Name:", value="", placeholder="Type SKU code or description (e.g. AN000648)...").strip()
    
    # Filter matrix dataframe dynamically based on search query
    if search_query:
        df_display_filtered = df_stock[
            df_stock["Item_Code"].astype(str).str.contains(search_query, case=False, na=False) |
            df_stock["Item_Name"].astype(str).str.contains(search_query, case=False, na=False)
        ]
    else:
        df_display_filtered = df_stock
            
    st.subheader("📊 Dynamic Global Stock Allocation Matrix")
    display_matrix = df_display_filtered[["Item_Code", "Item_Name", "Current_Stock", 
                               "Stock_Al_Quoz", "Stock_Sharjah", "Stock_DIP", "Stock_Abu_Dhabi", "Avg_Daily_Sales"]]
    st.dataframe(display_matrix, use_container_width=True, hide_index=True)
    
    st.markdown("### 💡 Recommended Optimization Routes")
    
    advisor_routes_found = False
    priority_destinations = ["Stock_Al_Quoz", "Stock_Sharjah", "Stock_DIP", "Stock_Abu_Dhabi"]
    
    # Generate recommendations using the filtered dataset to narrow down results when searching
    for idx, row in df_display_filtered.iterrows():
        sku = row["Item_Code"]
        name = row["Item_Name"]
        global_velocity = clean_float(row["Avg_Daily_Sales"])
        
        for dest_wh in priority_destinations:
            dest_qty = clean_float(row[dest_wh])
            days_of_coverage = dest_qty / global_velocity if global_velocity > 0 else 999
            
            if days_of_coverage <= 7.0:
                for source_wh in reversed(priority_destinations):
                    if source_wh == dest_wh:
                        continue
                        
                    src_qty = clean_float(row[source_wh])
                    src_coverage = src_qty / global_velocity if global_velocity > 0 else 0
                    
                    if src_coverage > 25.0:
                        target_replenish_qty = int((15 * global_velocity) - dest_qty)
                        donor_safe_limit = int(src_qty - (14 * global_velocity))
                        optimal_transfer = min(target_replenish_qty, donor_safe_limit)
                        
                        if optimal_transfer > 5:
                            clean_src = source_wh.replace("Stock_", "")
                            clean_dest = dest_wh.replace("Stock_", "")
                            
                            st.markdown(f"""
                                <div class="advice-card">
                                    🌐 <b>SKU Route Match:</b> <code>{sku}</code> — {name} <br/>
                                    ⚠️ <span class="critical-badge">{clean_dest}</span> holds critical deficit values ({int(dest_qty)} pcs | ~{days_of_coverage:.1f} days left).<br/>
                                    📦 <span class="surplus-badge">{clean_src}</span> has excess operational volume ({int(src_qty)} pcs).<br/>
                                    🚚 <b>Rational Suggestion:</b> Issue internal transfer of <b>{optimal_transfer} pcs</b> from {clean_src} to {clean_dest}.
                                </div>
                            """, unsafe_allow_html=True)
                            advisor_routes_found = True
                            break 
                            
    if not advisor_routes_found:
        if search_query:
            st.info(f"ℹ️ No transfer rules generated matching your search criteria: '{search_query}'.")
        else:
            st.success("✅ Multi-warehouse supply lines are evenly distributed. No critical stock deficits detected across active regions.")
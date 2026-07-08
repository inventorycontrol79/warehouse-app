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

url_params = st.query_params
if url_params.get("key", "") == "sabin_inventory":
    st.session_state.is_admin = True

is_admin = st.session_state.is_admin

# Premium High-Contrast Dark Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stSidebar"] div, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] a { 
        color: #FFFFFF !important; 
    }
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B !important; }
    
    [data-testid="stExpander"] { background-color: #111827 !important; border: 1px solid #1E293B !important; border-radius: 8px; }
    [data-testid="stExpander"] summary { color: #FFFFFF !important; }
    [data-testid="stFileUploader"] section { background-color: #111827 !important; border: 1px dashed #38BDF8 !important; }
    
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #FFFFFF !important; font-weight: 600 !important; }
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 11px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    .advice-card { background-color: #151F32; border-left: 4px solid #38BDF8; border-radius: 6px; padding: 16px; margin-bottom: 12px; border-top: 1px solid #1E293B; border-right: 1px solid #1E293B; border-bottom: 1px solid #1E293B; }
    .critical-badge { color: #F87171 !important; font-weight: 800; background-color: rgba(239, 68, 68, 0.15); padding: 4px 8px; border-radius: 4px; }
    .surplus-badge { color: #34D399 !important; font-weight: 800; background-color: rgba(52, 211, 153, 0.15); padding: 4px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

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
        ws = sh.get_worksheet(3) 
        data = ws.get_all_records()
        return pd.DataFrame(data), ws
    except Exception as e:
        st.error(f"🚨 Error Fetching Master Stock sheet: {e}")
        return pd.DataFrame(), None

df_stock, ws_stock_raw = pull_master_stock_data()

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
                    
                    st.success("🎉 Master database structure initialized successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Column structure mismatch. Ensure warehouse name suffixes are present.")
            except Exception as e:
                st.error(f"Initialization Failed: {e}")

# =====================================================
# 4. WORKSPACE PORTAL B: COLUMN-WISE SNAPSHOT INGESTION
# =====================================================
st.header("📥 Sync Daily Warehouse-Wise Stock Snapshot")
st.markdown("Upload your raw Focus multi-column inventory sheet. The dashboard will automatically update active tracking codes and match column metrics instantly.")

if df_stock.empty:
    st.info("ℹ️ Load Master Stock Sheets first before handling bulk files.")
elif not is_admin:
    st.warning("🔒 Device write lock is active. Please use your authenticated dashboard link to process files.")
else:
    uploaded_snap = st.file_uploader("Select Columnar ERP Warehouse Report (Excel/CSV)", type=["xlsx", "csv"])
    
    if uploaded_snap is not None:
        if st.button("⚡ EXECUTE SELECTIVE DASHBOARD OVERWRITE", use_container_width=True):
            try:
                # 1. Dynamic header tracking index scan
                if uploaded_snap.name.endswith(".csv"):
                    df_raw_check = pd.read_csv(uploaded_snap, header=None)
                else:
                    df_raw_check = pd.read_excel(uploaded_snap, header=None)
                
                header_row_idx = 0
                for idx, row_data in df_raw_check.iterrows():
                    row_strs = [str(cell).strip().lower() for cell in row_data.values]
                    # Identify by the key descriptive indicators found in your export image
                    if any("code" in s or "sku" in s for s in row_strs) and any("sharjah" in s or "quoz" in s for s in row_strs):
                        header_row_idx = idx
                        break
                
                if uploaded_snap.name.endswith(".csv"):
                    df_snap = pd.read_csv(uploaded_snap, skiprows=header_row_idx)
                else:
                    df_snap = pd.read_excel(uploaded_snap, skiprows=header_row_idx)
                
                # Standardize column strings
                df_snap.columns = [str(c).strip() for c in df_snap.columns]
                
                # Identify the main SKU column tracking field
                sku_col = next((c for c in df_snap.columns if "code" in c.lower() or "sku" in c.lower() or "item" in c.lower()), None)
                if not sku_col:
                    st.error("❌ Could not identify an 'Item Code' column in the uploaded snapshot layout.")
                    st.stop()
                
                # Map available columns inside your explicit Excel image file layout
                col_al_quoz = next((c for c in df_snap.columns if "al quoz" in c.lower() and "online" not in c.lower()), None)
                col_sharjah = next((c for c in df_snap.columns if "sharjah" in c.lower() and "online" not in c.lower()), None)
                col_dip = next((c for c in df_snap.columns if "dip" in c.lower()), None)
                col_abu_dhabi = next((c for c in df_snap.columns if "abu dhabi" in c.lower() or "ad" in c.lower()), None)
                
                # Online Columns (Read for calculations, hidden from visual data blocks)
                col_online_quoz = next((c for c in df_snap.columns if "al quoz" in c.lower() and "online" in c.lower()), None)
                col_online_shj = next((c for c in df_snap.columns if "sharjah" in c.lower() and "online" in c.lower()), None)
                
                updated_master_df = df_stock.copy()
                
                # Convert active Master entries into indexed dictionaries for efficient parsing loops
                snap_dict = {}
                for _, row in df_snap.iterrows():
                    s_code = str(row[sku_col]).strip()
                    if s_code:
                        snap_dict[s_code] = row

                matched_count = 0
                
                # Update loop mapped against only what currently exists inside your Master sheet
                for idx, m_row in updated_master_df.iterrows():
                    m_sku = str(m_row["Item_Code"]).strip()
                    
                    if m_sku in snap_dict:
                        erp_row = snap_dict[m_sku]
                        
                        # Direct assignment with fallback values
                        q_shj = pd.to_numeric(erp_row[col_sharjah], errors="coerce") if col_sharjah else 0.0
                        q_aq = pd.to_numeric(erp_row[col_al_quoz], errors="coerce") if col_al_quoz else 0.0
                        q_dip = pd.to_numeric(erp_row[col_dip], errors="coerce") if col_dip else 0.0
                        q_ad = pd.to_numeric(erp_row[col_abu_dhabi], errors="coerce") if col_abu_dhabi else 0.0
                        
                        # Online components read strictly for global total mapping
                        q_on_aq = pd.to_numeric(erp_row[col_online_quoz], errors="coerce") if col_online_quoz else 0.0
                        q_on_shj = pd.to_numeric(erp_row[col_online_shj], errors="coerce") if col_online_shj else 0.0
                        
                        # Write physical metrics back down to your working dataframe
                        updated_master_df.at[idx, "Stock_Sharjah"] = float(np.nan_to_num(q_shj))
                        updated_master_df.at[idx, "Stock_Al_Quoz"] = float(np.nan_to_num(q_aq))
                        updated_master_df.at[idx, "Stock_DIP"] = float(np.nan_to_num(q_dip))
                        updated_master_df.at[idx, "Stock_Abu_Dhabi"] = float(np.nan_to_num(q_ad))
                        
                        # Comprehensive Total includes physical warehouses + hidden online buckets!
                        updated_master_df.at[idx, "Current_Stock"] = float(
                            np.nan_to_num(q_shj) + np.nan_to_num(q_aq) + 
                            np.nan_to_num(q_dip) + np.nan_to_num(q_ad) + 
                            np.nan_to_num(q_on_aq) + np.nan_to_num(q_on_shj)
                        )
                        matched_count += 1
                
                if matched_count > 0:
                    def serialize_cell(val):
                        if pd.isna(val) or val is None or str(val).strip().lower() in ['nan', 'nat', 'inf', '-inf']:
                            return ""
                        return str(val).strip()
                    
                    clean_rows = updated_master_df[TARGET_COLUMNS].map(serialize_cell).values.tolist()
                    
                    gc = get_google_client()
                    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
                    ws_stock_write = sh.get_worksheet(3)
                    
                    ws_stock_write.clear()
                    ws_stock_write.append_rows([TARGET_COLUMNS] + clean_rows)
                    
                    st.success(f"🎉 Columns matched cleanly! Synchronized totals for {matched_count} tracked inventory profiles.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("⚠️ High volume file did not contain any matching SKU codes.")
            except Exception as e:
                st.error(f"🚨 Operational Snapshot Failure: {e}")

st.markdown("---")

# =====================================================
# 5. WORKSPACE PORTAL C: FORESIGHT ADVISOR WITH OVERRIDES
# =====================================================
st.header("🧠 Intelligent Supply Redistribution Advisor")

if df_stock.empty:
    st.info("ℹ️ Master allocation workspace balances are loading.")
else:
    def clean_float(value):
        try: return float(value) if str(value).strip() != "" else 0.0
        except: return 0.0

    for k in ["Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi", "Avg_Daily_Sales"]:
        if k not in df_stock.columns: df_stock[k] = 0

    col_search, col_vel_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Matrix or Advisor by SKU / Item Name:", value="", placeholder="Type SKU code...").strip()
    with col_vel_filter:
        min_velocity = st.number_input("📉 Minimum Daily Sales Velocity (Filter out slow items):", min_value=0.0, max_value=50.0, value=0.0, step=0.1)

    df_filtered = df_stock.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["Item_Code"].astype(str).str.contains(search_query, case=False, na=False) |
            df_filtered["Item_Name"].astype(str).str.contains(search_query, case=False, na=False)
        ]
    
    df_filtered = df_filtered[df_filtered["Avg_Daily_Sales"].apply(clean_float) >= min_velocity]
            
    st.subheader("📊 Dynamic Global Stock Allocation Matrix")
    # Displays physical locations only. Hidden online volumes are safely accounted for in "Current_Stock"
    st.dataframe(df_filtered[["Item_Code", "Item_Name", "Current_Stock", 
                               "Stock_Al_Quoz", "Stock_Sharjah", "Stock_DIP", "Stock_Abu_Dhabi", "Avg_Daily_Sales"]], 
                 use_container_width=True, hide_index=True)
    
    st.markdown("### 💡 Recommended Optimization Routes & Interactive Prep Console")
    
    advisor_routes_found = False
    priority_destinations = ["Stock_Al_Quoz", "Stock_Sharjah", "Stock_DIP", "Stock_Abu_Dhabi"]
    
    for idx, row in df_filtered.iterrows():
        sku = row["Item_Code"]
        name = row["Item_Name"]
        global_velocity = clean_float(row["Avg_Daily_Sales"])
        
        for dest_wh in priority_destinations:
            dest_qty = clean_float(row[dest_wh])
            days_of_coverage = dest_qty / global_velocity if global_velocity > 0 else 999
            
            if days_of_coverage <= 7.0:
                for source_wh in reversed(priority_destinations):
                    if source_wh == dest_wh: continue
                        
                    src_qty = clean_float(row[source_wh])
                    src_coverage = src_qty / global_velocity if global_velocity > 0 else 0
                    
                    if src_coverage > 25.0:
                        target_replenish_qty = int((15 * global_velocity) - dest_qty)
                        donor_safe_limit = int(src_qty - (14 * global_velocity))
                        optimal_transfer = min(target_replenish_qty, donor_safe_limit)
                        
                        if optimal_transfer > 5:
                            clean_src = source_wh.replace("Stock_", "")
                            clean_dest = dest_wh.replace("Stock_", "")
                            advisor_routes_found = True
                            
                            with st.container():
                                st.markdown(f"**🌐 Route Matched: `{sku}` — {name}**")
                                c1, c2, c3 = st.columns([2, 1, 1])
                                with c1:
                                    st.markdown(f"""
                                        ⚠️ <span class="critical-badge">{clean_dest}</span> holds critical low stock ({int(dest_qty)} pcs | ~{days_of_coverage:.1f} days left).<br/>
                                        📦 <span class="surplus-badge">{clean_src}</span> has safe excess volume available ({int(src_qty)} pcs).
                                    """, unsafe_allow_html=True)
                                with c2:
                                    final_qty = st.number_input(f"Adjust Qty ({sku})", min_value=1, max_value=int(src_qty), value=int(optimal_transfer), key=f"adj_{sku}_{clean_dest}")
                                with c3:
                                    erp_string = f"SRTS: Move {final_qty} pcs of SKU {sku} from {clean_src} to {clean_dest}"
                                    st.text_input("📋 Focus ERP Ready Command String:", value=erp_string, readonly=True, key=f"cmd_{sku}_{clean_dest}")
                                st.markdown("<div style='border-bottom: 1px dashed #1E293B; margin: 15px 0;'></div>", unsafe_allow_html=True)
                            break 
                            
    if not advisor_routes_found:
        st.success("✅ No inventory redistribution triggers match current filter limits.")
import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="SABIN PLASTIC // Stock Transfer Hub", layout="wide")

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

url_params = st.query_params
if url_params.get("key", "") == "sabin_inventory":
    st.session_state.is_admin = True

is_admin = st.session_state.is_admin

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    [data-testid="stSidebar"] div, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #FFFFFF !important; }
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B !important; }
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #FFFFFF !important; font-weight: 600 !important; }
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 11px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    .route-container { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .critical-badge { color: #F87171 !important; font-weight: 800; background-color: rgba(239, 68, 68, 0.15); padding: 4px 8px; border-radius: 4px; }
    .surplus-badge { color: #34D399 !important; font-weight: 800; background-color: rgba(52, 211, 153, 0.15); padding: 4px 8px; border-radius: 4px; }
    .idle-badge { color: #FB923C !important; font-weight: 800; background-color: rgba(251, 146, 60, 0.15); padding: 4px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='premium-header'><div class='sabin-logo'>SABIN <span>PLASTIC</span></div><div class='sabin-sub'>Multi-Warehouse Stock Transfer & Demand Planner</div></div>", unsafe_allow_html=True)

def get_google_client():
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Authentication Link Failed: {e}")
        return None

@st.cache_data(ttl=10)
def pull_master_database_payload():
    gc = get_google_client()
    if not gc: return pd.DataFrame(), pd.DataFrame(), None, None
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        ws_stock = sh.get_worksheet(3) 
        
        try:
            ws_snapshot_log = sh.worksheet("Daily_Snapshot_Log")
            df_l = pd.DataFrame(ws_snapshot_log.get_all_records())
        except Exception:
            df_l = pd.DataFrame() 
            
        df_s = pd.DataFrame(ws_stock.get_all_records())
        return df_s, df_l, ws_stock, ws_snapshot_log if 'ws_snapshot_log' in locals() else None
    except Exception as e:
        st.error(f"🚨 Database Payload Read Failure: {e}")
        return pd.DataFrame(), pd.DataFrame(), None, None

df_stock, df_logs, ws_stock, ws_snapshot_log = pull_master_database_payload()

MASTER_TRACKING_COLS = [
    "Item_Code", "Item_Name", "Product_Category", "Current_Stock",
    "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi",
    "ABC_Category", "Avg_Daily_Sales", "Last_Sold_Date", "Days_of_Coverage",
    "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"
]

if not df_stock.empty:
    for c in MASTER_TRACKING_COLS:
        if c not in df_stock.columns: 
            df_stock[c] = 0.0 if "Velocity" in c or "Stock" in c or c == "Avg_Daily_Sales" else ""

# ==========================================
#  🧠 RUNNING MEMORY LEARNING ENGINE (WITH AUTOMATED SALES RETURNS NETTING)
# ==========================================
if not df_logs.empty and not df_stock.empty:
    df_logs.columns = [str(c).strip() for c in df_logs.columns]
    
    # Accept either standard tracking label or direct Focus column name
    type_col = "Transaction_Type" if "Transaction_Type" in df_logs.columns else ("Voucher abbreviation" if "Voucher abbreviation" in df_logs.columns else None)
    
    if "Item_Code" in df_logs.columns and "Qty_Delta" in df_logs.columns and type_col:
        df_logs["Qty_Delta"] = pd.to_numeric(df_logs["Qty_Delta"], errors="coerce").fillna(0.0).abs()
        
        # Calculate true Net Quantities: SINVS/Sales add to velocity, SRTS subtracts from velocity
        def calculate_net_sales_volume(row):
            voucher_type = str(row[type_col]).strip().upper()
            qty = float(row["Qty_Delta"])
            if voucher_type == "SRTS":
                return -qty
            elif voucher_type in ["SINVS", "SALES"]:
                return qty
            return 0.0

        df_logs["Net_Qty"] = df_logs.apply(calculate_net_sales_volume, axis=1)
        df_sales = df_logs[df_logs["Net_Qty"] != 0.0]
        
        if not df_sales.empty:
            unique_dates_in_file = pd.to_datetime(df_sales["Timestamp"]).dt.date.nunique()
            unique_dates_in_file = max(1, unique_dates_in_file)
            
            july_1st = datetime(2026, 7, 1).date()
            today_date = datetime.now().date()
            days_elapsed_total = max(1, (today_date - july_1st).days + 1)
            
            is_initialization = unique_dates_in_file > 2
            
            upload_global_totals = df_sales.groupby("Item_Code")["Net_Qty"].sum().to_dict()
            
            warehouse_selectors = {
                "Al Quoz": "Velocity_Al_Quoz",
                "Sharjah": "Velocity_Sharjah",
                "DIP": "Velocity_DIP",
                "Abu Dhabi": "Velocity_Abu_Dhabi"
            }
            
            upload_branch_totals = {}
            for branch_keyword, column_target in warehouse_selectors.items():
                b_df = df_sales[df_sales["Branch"].astype(str).str.contains(branch_keyword, case=False, na=False)]
                upload_branch_totals[branch_keyword] = b_df.groupby("Item_Code")["Net_Qty"].sum().to_dict() if not b_df.empty else {}

            for idx, row in df_stock.iterrows():
                sku = str(row["Item_Code"]).strip()
                
                # Global Net Average Updates
                file_global_net = upload_global_totals.get(sku, 0.0)
                if is_initialization:
                    df_stock.at[idx, "Avg_Daily_Sales"] = max(0.0, round(file_global_net / unique_dates_in_file, 2))
                else:
                    old_global_avg = float(row["Avg_Daily_Sales"]) if pd.notna(row["Avg_Daily_Sales"]) else 0.0
                    df_stock.at[idx, "Avg_Daily_Sales"] = max(0.0, round(((old_global_avg * (days_elapsed_total - 1)) + file_global_net) / days_elapsed_total, 2))
                
                # Location Specific Net Velocity Updates
                for branch_keyword, column_target in warehouse_selectors.items():
                    file_branch_net = upload_branch_totals[branch_keyword].get(sku, 0.0)
                    if is_initialization:
                        df_stock.at[idx, column_target] = max(0.0, round(file_branch_net / unique_dates_in_file, 2))
                    else:
                        old_branch_velocity = float(row[column_target]) if pd.notna(row[column_target]) else 0.0
                        df_stock.at[idx, column_target] = max(0.0, round(((old_branch_velocity * (days_elapsed_total - 1)) + file_branch_net) / days_elapsed_total, 2))

            def serialize_cell(val):
                return "" if pd.isna(val) or str(val).strip().lower() in ['nan', 'nat', 'inf'] else str(val).strip()
            
            clean_rows = df_stock[MASTER_TRACKING_COLS].map(serialize_cell).values.tolist()
            ws_stock.clear()
            ws_stock.append_rows([MASTER_TRACKING_COLS] + clean_rows)
            
            st.success("🧠 Memory Pattern Updated! The algorithm has safely processed net sales (Invoices minus Returns) and saved velocities into your Master sheet. You can now clear out the data inside the 'Daily_Snapshot_Log' tab.")

# Recalculate runway numbers
if not df_stock.empty:
    for k in ["Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi", "Avg_Daily_Sales",
              "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"]:
        df_stock[k] = pd.to_numeric(df_stock[k], errors='coerce').fillna(0.0)
    
    df_stock["Days_of_Coverage"] = df_stock.apply(
        lambda r: 999 if r["Avg_Daily_Sales"] <= 0 else round(r["Current_Stock"] / r["Avg_Daily_Sales"], 1), axis=1
    )

# ==========================================
#  INVENTORY MATRIX SNAPSHOT OVERWRITE
# ==========================================
st.subheader("📥 Reconcile Physical Warehouse Stock Snapshot")
st.markdown("<small>Upload your clean Focus matrix file here to update the on-hand quantities across locations.</small>", unsafe_allow_html=True)

if df_stock.empty:
    st.info("ℹ️ Loading balance tables from cloud infrastructure...")
elif not is_admin:
    st.warning("🔒 Device write lock is active. Authentication parameters required to modify inventory records.")
else:
    uploaded_snap = st.file_uploader("Select Cleaned Warehouse Matrix Report (Excel/CSV)", type=["xlsx", "csv"], key="matrix_up")
    if uploaded_snap is not None and st.button("⚡ EXECUTE SELECTIVE BALANCE OVERWRITE"):
        try:
            df_snap = pd.read_csv(uploaded_snap) if uploaded_snap.name.endswith(".csv") else pd.read_excel(uploaded_snap)
            df_snap.columns = [str(c).strip() for c in df_snap.columns]
            
            if "Item_Code" not in df_snap.columns:
                st.error("❌ Schema Verification Error: Missing column exact label 'Item_Code'.")
                st.stop()
            
            updated_master_df = df_stock.copy()
            snap_dict = {str(row["Item_Code"]).strip(): row for _, row in df_snap.iterrows()}
            matched_count = 0
            
            def safe_float(val):
                res = pd.to_numeric(val, errors="coerce")
                return float(res) if pd.notna(res) else 0.0

            for idx, m_row in updated_master_df.iterrows():
                m_sku = str(m_row["Item_Code"]).strip()
                if m_sku in snap_dict:
                    erp_row = snap_dict[m_sku]
                    q_aq = safe_float(erp_row.get("Al Quoz Trading SP", 0))
                    q_shj = safe_float(erp_row.get("Sharjah Trading SP", 0))
                    q_ad = safe_float(erp_row.get("Abu Dhabi Trading SP", 0))
                    q_dip = safe_float(erp_row.get("DIP Trading", 0))
                    q_o_ad = safe_float(erp_row.get("Online Abu Dhabi Trading SP", 0))
                    q_o_aq = safe_float(erp_row.get("Online Al Quoz Trading SP", 0))
                    
                    updated_master_df.at[idx, "Stock_Sharjah"] = q_shj
                    updated_master_df.at[idx, "Stock_Al_Quoz"] = q_aq
                    updated_master_df.at[idx, "Stock_DIP"] = q_dip
                    updated_master_df.at[idx, "Stock_Abu_Dhabi"] = q_ad
                    updated_master_df.at[idx, "Current_Stock"] = float(q_shj + q_aq + q_ad + q_dip + q_o_ad + q_o_aq)
                    matched_count += 1
            
            if matched_count > 0:
                def serialize_cell(val):
                    return "" if pd.isna(val) or str(val).strip().lower() in ['nan', 'nat', 'inf'] else str(val).strip()
                clean_rows = updated_master_df[MASTER_TRACKING_COLS].map(serialize_cell).values.tolist()
                ws_stock.clear()
                ws_stock.append_rows([MASTER_TRACKING_COLS] + clean_rows)
                st.success(f"🎉 Snapshot mapped successfully for {matched_count} tracked inventory items!")
                st.cache_data.clear()
                st.rerun()
        except Exception as e:
            st.error(f"🚨 Snapshot Balance Overwrite Failure: {e}")

st.markdown("---")
st.header("🧠 Intelligent Supply Redistribution Advisor (Demand Planner)")

if df_stock.empty:
    st.info("ℹ️ Processing real-time ledger distributions...")
else:
    col_search, col_vel_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Matrix or Planner by SKU / Item Name:", value="").strip()
    with col_vel_filter:
        min_velocity = st.number_input("📉 Minimum Global Daily Sales Velocity Filter:", min_value=0.0, value=0.0)

    df_filtered = df_stock.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["Item_Code"].astype(str).str.contains(search_query, case=False, na=False) |
            df_filtered["Item_Name"].astype(str).str.contains(search_query, case=False, na=False)
        ]
    df_filtered = df_filtered[df_filtered["Avg_Daily_Sales"] >= min_velocity]

    st.subheader("📊 Dynamic Global Stock Allocation Matrix")
    st.dataframe(
        df_filtered[["Item_Code", "Item_Name", "Current_Stock", "Stock_Al_Quoz", "Stock_Sharjah", "Stock_DIP", "Stock_Abu_Dhabi", 
                     "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"]], 
        hide_index=True,
        column_config={
            "Velocity_Al_Quoz": "Velo AQ", "Velocity_Sharjah": "Velo SHJ", "Velocity_DIP": "Velo DIP", "Velocity_Abu_Dhabi": "Velo AD",
            "Stock_Al_Quoz": "Stock AQ", "Stock_Sharjah": "Stock SHJ", "Stock_DIP": "Stock DIP", "Stock_Abu_Dhabi": "Stock AD"
        }
    )

    st.markdown("### 💡 Recommended Optimization Routes")
    advisor_routes_found = False
    
    warehouse_mappings = [
        {"stock_col": "Stock_Al_Quoz", "vel_col": "Velocity_Al_Quoz", "label": "Al Quoz"},
        {"stock_col": "Stock_Sharjah", "vel_col": "Velocity_Sharjah", "label": "Sharjah"},
        {"stock_col": "Stock_DIP", "vel_col": "Velocity_DIP", "label": "DIP"},
        {"stock_col": "Stock_Abu_Dhabi", "vel_col": "Velocity_Abu_Dhabi", "label": "Abu Dhabi"}
    ]
    
    for idx, row in df_filtered.iterrows():
        sku = row["Item_Code"]
        name = row["Item_Name"]
        
        for dest in warehouse_mappings:
            dest_qty = row[dest["stock_col"]]
            dest_vel = row[dest["vel_col"]]
            
            if dest_vel > 0:
                dest_coverage = dest_qty / dest_vel
                trigger_routing = (dest_coverage <= 10.0)
            else:
                dest_coverage = 999
                trigger_routing = False
                
            if trigger_routing:
                for src in warehouse_mappings:
                    if src["stock_col"] == dest["stock_col"]: 
                        continue
                        
                    src_qty = row[src["stock_col"]]
                    src_vel = row[src["vel_col"]]
                    
                    if src_vel > 0:
                        src_coverage = src_qty / src_vel
                        is_eligible_donor = (src_coverage > 25.0 and src_qty > 5)
                        donor_status_msg = f"holds safety cushions (~{src_coverage:.1f} days runway)"
                        badge_style = "surplus-badge"
                    else:
                        src_coverage = 999
                        is_eligible_donor = (src_qty >= 1)
                        donor_status_msg = "holds completely IDLE inventory (0 local sales this month)"
                        badge_style = "idle-badge"
                        
                    if is_eligible_donor:
                        target_replenish_qty = int((20 * dest_vel) - dest_qty)
                        donor_safe_limit = int(src_qty - (15 * src_vel)) if src_vel > 0 else int(src_qty)
                        optimal_transfer = min(target_replenish_qty, donor_safe_limit)
                        
                        if optimal_transfer >= 1:
                            advisor_routes_found = True
                            
                            st.markdown(f"<div class='route-container'>", unsafe_allow_html=True)
                            st.markdown(f"**🌐 Balancing Optimization Route Matched: `{sku}` — {name}**")
                            c1, c2, c3 = st.columns([2, 1, 1])
                            with c1:
                                st.markdown(f"""
                                    ⚠️ Deficit Area: <span class='critical-badge'>{dest['label']}</span> runs hot ({int(dest_qty)} units left | local demand consumes **{dest_vel:.2f} units/day** &rarr; **{dest_coverage:.1f} days runway**).<br/>
                                    📦 Surplus Area: <span class='{badge_style}'>{src['label']}</span> {donor_status_msg} ({int(src_qty)} units on hand).
                                """, unsafe_allow_html=True)
                            with c2:
                                final_qty = st.number_input(f"Confirm Transfer Quantity ({sku})", min_value=1, max_value=int(src_qty), value=int(optimal_transfer), key=f"tr_{sku}_{dest['label']}")
                            with c3:
                                erp_string = f"SRTS: Move {final_qty} units of SKU {sku} from {src['label']} to {dest['label']}"
                                st.text_input("📋 Focus ERP Direct Command Output:", value=erp_string, disabled=True, key=f"cmd_{sku}_{dest['label']}")
                            st.markdown("</div>", unsafe_allow_html=True)
                            break 
                            
    if not advisor_routes_found:
        st.success("✅ Smart Supply Chains Aligned: All location inventory metrics balance accurately against their respective sales trends.")
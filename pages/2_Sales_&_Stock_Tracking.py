import streamlit as st
import pandas as pd
import numpy as np
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

def get_fresh_google_sheet_file():
    gc = get_google_client()
    if not gc: return None
    try: return gc.open_by_url(st.secrets["GSHEET_URL"])
    except Exception: return None

@st.cache_data(ttl=10)
def pull_master_database_payload():
    gc = get_google_client()
    if not gc: return pd.DataFrame(), pd.DataFrame()
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        def safe_worksheet_to_df(ws):
            raw_grid = ws.get_all_values()
            if not raw_grid: return pd.DataFrame()
            headers = [str(h).strip() for h in raw_grid[0]]
            rows = raw_grid[1:]
            df = pd.DataFrame(rows, columns=headers)
            if "" in df.columns: df = df.drop(columns=[""])
            return df

        ws_stock = sh.get_worksheet(3) 
        df_s = safe_worksheet_to_df(ws_stock)
        try:
            ws_snapshot_log = sh.worksheet("Daily_Snapshot_Log")
            df_l = safe_worksheet_to_df(ws_snapshot_log)
        except Exception: df_l = pd.DataFrame() 
            
        return df_s, df_l
    except Exception as e:
        st.error(f"🚨 Database Payload Read Failure: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_stock, df_logs = pull_master_database_payload()

MASTER_TRACKING_COLS = [
    "Item_Code", "Item_Name", "Product_Category", "Current_Stock",
    "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi",
    "ABC_Category", "Avg_Daily_Sales", "Baseline_Velocity", "Consistency_Score",
    "Total_Lifetime_Sales", "Lifespan_Days", "Last_Sold_Date", "Last_Updated_Date",
    "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"
]

if not df_stock.empty:
    for c in MASTER_TRACKING_COLS:
        if c not in df_stock.columns: 
            df_stock[c] = 0.0 if any(k in c for k in ["Velocity", "Stock", "Sales", "Score", "Days"]) else ""

    for k in ["Current_Stock", "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi", 
              "Avg_Daily_Sales", "Baseline_Velocity", "Consistency_Score",
              "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"]:
        df_stock[k] = pd.to_numeric(df_stock[k], errors='coerce').fillna(0.0)
    
    df_stock["Days_of_Coverage"] = df_stock.apply(
        lambda r: 999 if r["Baseline_Velocity"] <= 0 else round(r["Current_Stock"] / r["Baseline_Velocity"], 1), axis=1
    )

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
            
            cols = df_snap.columns.tolist()
            
            def find_smart_col(keywords):
                for kw in keywords:
                    for c in cols:
                        if kw.lower() in c.lower():
                            return c
                return None

            col_code = find_smart_col(["item_code", "item.code", "item code", "code"])
            col_name = find_smart_col(["item_name", "item.name", "item name", "description", "specification"])
            
            col_shj = find_smart_col(["sharjah"])
            col_aq = find_smart_col(["al quoz", "al_quoz", "quoz", "dubai"])
            col_dip = find_smart_col(["dip"])
            col_ad = find_smart_col(["abu dhabi", "abu_dhabi", "ad trading"])
            col_online_ad = find_smart_col(["online abu dhabi", "online_ad"])
            col_online_aq = find_smart_col(["online al quoz", "online_aq"])

            if not col_code:
                st.error(f"❌ Schema Error: Could not detect Item Code column. Found headers: {cols}")
                st.stop()
            
            updated_master_df = df_stock.copy()
            
            def clean_code_str(val):
                return str(val).split('.')[0].strip().upper()

            def clean_name_str(val):
                return str(val).strip().upper()

            snap_map_composite = {}
            snap_map_code_only = {}

            for _, row in df_snap.iterrows():
                c_code = clean_code_str(row[col_code])
                c_name = clean_name_str(row[col_name]) if col_name and pd.notna(row[col_name]) else ""
                
                comp_key = f"{c_code}|||{c_name}"
                snap_map_composite[comp_key] = row
                snap_map_code_only[c_code] = row

            matched_count = 0
            
            def safe_float(val):
                res = pd.to_numeric(val, errors="coerce")
                return float(res) if pd.notna(res) else 0.0

            for idx, m_row in updated_master_df.iterrows():
                m_code = clean_code_str(m_row["Item_Code"])
                m_name = clean_name_str(m_row["Item_Name"])
                comp_key = f"{m_code}|||{m_name}"

                target_row = None
                if comp_key in snap_map_composite:
                    target_row = snap_map_composite[comp_key]
                elif m_code in snap_map_code_only:
                    target_row = snap_map_code_only[m_code]

                if target_row is not None:
                    q_shj = safe_float(target_row[col_shj]) if col_shj else 0.0
                    q_aq = safe_float(target_row[col_aq]) if col_aq else 0.0
                    q_dip = safe_float(target_row[col_dip]) if col_dip else 0.0
                    q_ad = safe_float(target_row[col_ad]) if col_ad else 0.0
                    q_o_ad = safe_float(target_row[col_online_ad]) if col_online_ad else 0.0
                    q_o_aq = safe_float(target_row[col_online_aq]) if col_online_aq else 0.0

                    updated_master_df.at[idx, "Stock_Sharjah"] = q_shj
                    updated_master_df.at[idx, "Stock_Al_Quoz"] = q_aq + q_o_aq
                    updated_master_df.at[idx, "Stock_DIP"] = q_dip
                    updated_master_df.at[idx, "Stock_Abu_Dhabi"] = q_ad + q_o_ad
                    updated_master_df.at[idx, "Current_Stock"] = float(q_shj + q_aq + q_dip + q_ad + q_o_ad + q_o_aq)
                    matched_count += 1
            
            if matched_count > 0:
                def serialize_cell(val):
                    return "" if pd.isna(val) or str(val).strip().lower() in ['nan', 'nat', 'inf'] else str(val).strip()
                
                fresh_sh = get_fresh_google_sheet_file()
                if fresh_sh:
                    fresh_ws_stock = fresh_sh.get_worksheet(3)
                    clean_rows = updated_master_df[MASTER_TRACKING_COLS].map(serialize_cell).values.tolist()
                    fresh_ws_stock.clear()
                    fresh_ws_stock.append_rows([MASTER_TRACKING_COLS] + clean_rows)
                    st.success(f"🎉 Snapshot successfully matched and overwritten for {matched_count} SKUs!")
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("🚨 Cloud Connection busy. Please try executing the upload action again.")
            else:
                st.warning("⚠️ Zero items matched between your uploaded snapshot and the database. Check if Item Codes match.")
        except Exception as e:
            st.error(f"🚨 Snapshot Balance Overwrite Failure: {e}")

st.markdown("---")
st.header("🧠 Intelligent Supply Redistribution Advisor (DOI Balancing Engine)")

if df_stock.empty:
    st.info("ℹ️ Processing real-time ledger distributions...")
else:
    col_search, col_vel_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Matrix or Planner by SKU / Item Name:", value="").strip()
    with col_vel_filter:
        min_velocity = st.number_input("📉 Minimum Baseline Velocity Filter:", min_value=0.0, value=0.0)

    df_filtered = df_stock.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["Item_Code"].astype(str).str.contains(search_query, case=False, na=False) |
            df_filtered["Item_Name"].astype(str).str.contains(search_query, case=False, na=False)
        ]
    df_filtered = df_filtered[df_filtered["Baseline_Velocity"] >= min_velocity]

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

    st.markdown("### 💡 Recommended Optimization Routes (Proportional Base-Stock Equalization)")
    
    wh_options = ["All Warehouses", "Al Quoz", "Sharjah", "DIP", "Abu Dhabi"]
    selected_wh = st.selectbox("📍 Filter Optimization Feed by Supervisor Location:", options=wh_options, index=0)
    
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
        total_system_stock = float(row["Current_Stock"])
        
        total_net_vel = sum(float(row[w["vel_col"]]) for w in warehouse_mappings)
        
        if total_net_vel <= 0 or total_system_stock <= 0:
            continue

        branch_needs = []
        for w in warehouse_mappings:
            b_vel = float(row[w["vel_col"]])
            b_stock = float(row[w["stock_col"]])
            
            demand_share = b_vel / total_net_vel if total_net_vel > 0 else 0.25
            target_stock = total_system_stock * demand_share
            net_need = target_stock - b_stock
            
            b_runway = (b_stock / b_vel) if b_vel > 0 else 999.0
            
            branch_needs.append({
                "label": w["label"],
                "stock_col": w["stock_col"],
                "vel_col": w["vel_col"],
                "stock": b_stock,
                "vel": b_vel,
                "runway": b_runway,
                "net_need": net_need
            })

        deficits = [b for b in branch_needs if b["net_need"] > 1.0 and b["runway"] < 12.0]
        surpluses = [b for b in branch_needs if b["net_need"] < -1.0 or (b["vel"] == 0 and b["stock"] >= 1)]

        for dest in deficits:
            for src in surpluses:
                if dest["label"] == src["label"]: continue
                
                if selected_wh != "All Warehouses":
                    if dest["label"] != selected_wh and src["label"] != selected_wh:
                        continue

                if src["vel"] > 0:
                    src_safe_donor_limit = max(0, int(src["stock"] - (10.0 * src["vel"])))
                    donor_status_msg = f"holds surplus runway (~{src['runway']:.1f} days)"
                    badge_style = "surplus-badge"
                else:
                    src_safe_donor_limit = int(src["stock"])
                    donor_status_msg = "holds IDLE inventory (0 local sales)"
                    badge_style = "idle-badge"

                optimal_transfer = min(int(dest["net_need"]), src_safe_donor_limit)
                
                if optimal_transfer >= 1:
                    advisor_routes_found = True
                    
                    st.markdown(f"<div class='route-container'>", unsafe_allow_html=True)
                    st.markdown(f"**🌐 Proportional Optimization Route: `{sku}` — {name}**")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        st.markdown(f"""
                            ⚠️ Deficit Area: <span class='critical-badge'>{dest['label']}</span> runs low ({int(dest['stock'])} units | run-rate **{dest['vel']:.2f}/day** &rarr; **{dest['runway']:.1f} days runway**).<br/>
                            📦 Donor Area: <span class='{badge_style}'>{src['label']}</span> {donor_status_msg} ({int(src['stock'])} units on hand).
                        """, unsafe_allow_html=True)
                    with c2:
                        final_qty = st.number_input(
                            f"Confirm Transfer Quantity ({sku})", 
                            min_value=1, 
                            max_value=max(1, int(src["stock"])), 
                            value=int(optimal_transfer), 
                            key=f"tr_{idx}_{sku}_{dest['label']}_{src['label']}"
                        )
                    with c3:
                        erp_string = f"SRTS: Move {final_qty} units of SKU {sku} from {src['label']} to {dest['label']}"
                        st.text_input("📋 Focus ERP Direct Command Output:", value=erp_string, disabled=True, key=f"cmd_{idx}_{sku}_{dest['label']}_{src['label']}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    break 

    if not advisor_routes_found:
        if selected_wh != "All Warehouses":
            st.success(f"✅ Smart Supply Chains Aligned: **{selected_wh}** does not require any replenishment or stock-shifting operations right now.")
        else:
            st.success("✅ Smart Supply Chains Aligned: All location inventory metrics balance accurately against their respective sales trends.")
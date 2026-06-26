import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="SABIN PLASTIC // Inventory Intelligence", layout="wide")

# --- SECRET KEY ADMIN ACCESS GATEWAY ---
url_params = st.query_params
is_admin = url_params.get("key", "") == "sabin_inventory"

# --- PREMIUM HIGH-CONTRAST ERP STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #94A3B8 !important; font-weight: 600 !important; }
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 12px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    section[data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B; }
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1E293B; border-top: 3px solid #0EA5E9; border-radius: 6px; padding: 20px; }
    .upload-box { background-color: #111827; border: 1px dashed #1E293B; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='premium-header'><div class='sabin-logo'>SABIN <span>PLASTIC</span></div><div class='sabin-sub'>Enterprise Warehouse Tracking System</div></div>", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION INTERFACE ---
def get_google_client():
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Authentication Failed: {e}")
        return None

def get_worksheets():
    gc = get_google_client()
    if not gc: return None, None, None
    sh = gc.open_by_url(st.secrets["GSHEET_URL"])
    return sh.get_worksheet(3), sh.get_worksheet(4), sh.get_worksheet(5)

def load_data_from_sheet(ws, fallback_cols):
    try:
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=fallback_cols)
    except Exception:
        return pd.DataFrame(columns=fallback_cols)

# --- INGEST SHEETS ---
ws_stock, ws_log, ws_batches = get_worksheets()

df_stock = load_data_from_sheet(ws_stock, ["Item_Code", "Item_Name", "Current_Stock", "ABC_Category", "Avg_Daily_Sales"])
df_log = load_data_from_sheet(ws_log, ["Date", "Item_Code", "Item_Name", "Transaction_Type", "Qty_Delta", "Voucher_Reference", "Timestamp"])
df_batches = load_data_from_sheet(ws_batches, ["Batch_ID", "Upload_Type", "Timestamp"])

# Clean up baseline string spaces
for d in [df_stock, df_log, df_batches]:
    if not d.empty:
        for col in d.columns:
            if d[col].dtype == 'object': d[col] = d[col].astype(str).str.strip()

# --- RECALCULATE ABC CATEGORIES & RUNNING STATS ---
def recalculate_abc_and_velocity(stock_df, log_df):
    if log_df.empty or stock_df.empty:
        return stock_df
        
    # Standardize data formats
    log_df["Qty_Delta"] = pd.to_numeric(log_df["Qty_Delta"], errors='coerce').fillna(0)
    log_df["Timestamp"] = pd.to_datetime(log_df["Timestamp"], errors='coerce')
    
    # Filter for Sales over a rolling 30 days window
    thirty_days_ago = datetime.now() - timedelta(days=30)
    sales_30 = log_df[(log_df["Transaction_Type"] == "Sales") & (log_df["Timestamp"] >= thirty_days_ago)]
    
    if sales_30.empty:
        stock_df["ABC_Category"] = "C"
        stock_df["Avg_Daily_Sales"] = 0.0
        return stock_df
        
    # Sum total sales quantity per item
    item_sales = sales_30.groupby("Item_Code")["Qty_Delta"].sum().reset_index()
    item_sales["Qty_Delta"] = item_sales["Qty_Delta"].abs() # Ensure tracking absolute usage values
    item_sales = item_sales.sort_values(by="Qty_Delta", ascending=False)
    
    # Calculate Pareto Distribution Metrics
    total_volume = item_sales["Qty_Delta"].sum()
    if total_volume > 0:
        item_sales["Cum_Percentage"] = item_sales["Qty_Delta"].cumsum() / total_volume
    else:
        item_sales["Cum_Percentage"] = 1.0
        
    def assign_abc(pct):
        if pct <= 0.80: return "A"
        elif pct <= 0.95: return "B"
        else: return "C"
        
    item_sales["ABC_Category"] = item_sales["Cum_Percentage"].apply(assign_abc)
    item_sales["Avg_Daily_Sales"] = round(item_sales["Qty_Delta"] / 30, 2)
    
    # Map updates back into Master Stock Profile
    stock_df.set_index("Item_Code", inplace=True)
    item_sales.set_index("Item_Code", inplace=True)
    
    stock_df.update(item_sales[["ABC_Category", "Avg_Daily_Sales"]])
    stock_df.reset_index(inplace=True)
    stock_df["ABC_Category"] = stock_df["ABC_Category"].fillna("C")
    stock_df["Avg_Daily_Sales"] = pd.to_numeric(stock_df["Avg_Daily_Sales"], errors='coerce').fillna(0.0)
    
    return stock_df

# --- SNAPSHOT KPIS SUMMARY ---
st.markdown("### 📊 Inventory Intelligence KPIs")
total_skus = len(df_stock) if not df_stock.empty else 0

# Calculate Days of Coverage safety limits
if not df_stock.empty:
    df_stock["Current_Stock"] = pd.to_numeric(df_stock["Current_Stock"], errors='coerce').fillna(0)
    df_stock["Avg_Daily_Sales"] = pd.to_numeric(df_stock["Avg_Daily_Sales"], errors='coerce').fillna(0.0)
    
    def calc_doc(row):
        if row["Avg_Daily_Sales"] <= 0: return 999 # Safe/No demand tracking
        return round(row["Current_Stock"] / row["Avg_Daily_Sales"], 1)
        
    df_stock["Days_of_Coverage"] = df_stock.apply(calc_doc, axis=1)
    
    stockout_count = len(df_stock[(df_stock["ABC_Category"] == "A") & (df_stock["Days_of_Coverage"] <= 7)])
    overstock_count = len(df_stock[(df_stock["ABC_Category"] == "C") & (df_stock["Days_of_Coverage"] >= 90)])
    a_count = len(df_stock[df_stock["ABC_Category"] == "A"])
else:
    stockout_count = overstock_count = a_count = 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("TOTAL TRACKED SKUS", total_skus)
kpi2.metric("FAST MOVING SKUS (CLASS A)", a_count)
kpi3.metric("CRITICAL STOCKOUT RISK (<7 DAYS)", stockout_count, delta="Check Class A", delta_color="inverse")
kpi4.metric("DEAD STOCK OVERFLOW (>90 DAYS)", overstock_count, delta="Check Class C", delta_color="off")

st.markdown("---")

# --- FILE INGESTION CONTROLS (GATED) ---
if not is_admin:
    st.info("🔒 Stock adjustments and data ingestion engines locked. Displaying running terminal logs in read-only mode.")
else:
    col_left, col_right = st.columns(2)
    
    # --- MODULE A: MATERIAL RECEIPT NOTES (MRN) ---
    with col_left:
        st.markdown("<div class='upload-box'><h5>📥 Process Incoming Stock (MRN File)</h5>", unsafe_allow_html=True)
        mrn_file = st.file_uploader("Upload MRN Excel (.xlsx)", type=["xlsx"], key="mrn_loader")
        if mrn_file:
            df_mrn_raw = pd.read_excel(mrn_file, engine="openpyxl")
            df_mrn_raw.columns = [str(c).strip() for c in df_mrn_raw.columns]
            
            # Map standard columns automatically based on user image selection
            req_mrn = ["Date", "Document No.", "Item.Code", "Item.Name", "Quantity"]
            if all(c in df_mrn_raw.columns for c in req_mrn):
                # Unique file reference serving as verification batch ID
                unique_batch = str(df_mrn_raw["Document No."].iloc[0]).strip()
                
                if not df_batches.empty and unique_batch in df_batches["Batch_ID"].values:
                    st.error(f"🛑 Double-Upload Blocked! Document Reference `{unique_batch}` has already been committed to stock.")
                else:
                    if st.button("⚡ INTEGRATE MRN ENTRY INTO STOCK", use_container_width=True):
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_logs, new_stock_map = [], {}
                        
                        # Process additions
                        for _, row in df_mrn_raw.iterrows():
                            icode = str(row["Item.Code"]).strip()
                            iname = str(row["Item.Name"]).strip()
                            qty = float(row["Quantity"])
                            
                            new_logs.append([str(row["Date"]), icode, iname, "MRN", qty, unique_batch, timestamp_str])
                            new_stock_map[icode] = {"Item_Name": iname, "Qty": qty}
                        
                        # Merge updates to the local snapshot
                        updated_stock = df_stock.copy()
                        for code, info in new_stock_map.items():
                            if not updated_stock.empty and code in updated_stock["Item_Code"].values:
                                updated_stock.loc[updated_stock["Item_Code"] == code, "Current_Stock"] += info["Qty"]
                            else:
                                new_row = pd.DataFrame([{"Item_Code": code, "Item_Name": info["Item_Name"], "Current_Stock": info["Qty"], "ABC_Category": "C", "Avg_Daily_Sales": 0.0}])
                                updated_stock = pd.concat([updated_stock, new_row], ignore_index=True)
                                
                        # Save execution logs back to Google Sheets
                        ws_stock.clear()
                        ws_stock.append_rows([updated_stock.columns.tolist()] + updated_stock.fillna("").astype(str).values.tolist())
                        ws_log.append_rows(new_logs)
                        ws_batches.append_rows([[unique_batch, "MRN", timestamp_str]])
                        
                        st.success(f"MRN Entry `{unique_batch}` processed! Stock profiles synchronized.")
                        st.rerun()
            else:
                st.error(f"Required headers matching structure missing. File must contain: {req_mrn}")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- MODULE B: DAILY SALES INGESTION ---
    with col_right:
        st.markdown("<div class='upload-box'><h5>📤 Process Outgoing Sales (Daily Ledger)</h5>", unsafe_allow_html=True)
        sales_file = st.file_uploader("Upload Yesterday's Sales Sheet (.xlsx)", type=["xlsx"], key="sales_loader")
        if sales_file:
            df_sales_raw = pd.read_excel(sales_file, engine="openpyxl")
            df_sales_raw.columns = [str(c).strip() for c in df_sales_raw.columns]
            
            # Map columns dynamically using flexible match lists
            cols = df_sales_raw.columns.tolist()
            def find_col(guesses):
                for g in guesses:
                    for c in cols:
                        if g.lower() in c.lower(): return c
                return cols[0] if cols else ""
                
            match_date = st.selectbox("Match Sales [Date]:", cols, index=cols.index(find_col(["date", "posting"])))
            match_vouch = st.selectbox("Match Sales [Voucher No]:", cols, index=cols.index(find_col(["document", "voucher", "invoice"])))
            match_code = st.selectbox("Match Sales [Item Code]:", cols, index=cols.index(find_col(["item.code", "item_code", "code"])))
            match_name = st.selectbox("Match Sales [Item Name]:", cols, index=cols.index(find_col(["item.name", "item_name", "description"])))
            match_qty = st.selectbox("Match Sales [Quantity]:", cols, index=cols.index(find_col(["quantity", "qty", "sold"])))
            
            sales_batch_id = str(df_sales_raw[match_vouch].iloc[0]).strip() + "_SALES"
            
            if not df_batches.empty and sales_batch_id in df_batches["Batch_ID"].values:
                st.error("🛑 Double-Upload Blocked! This specific daily sales file batch has already been deducted from inventory records.")
            else:
                if st.button("⚡ EXECUTE QUANTITY DEDUCTION & ABC ANALYSIS", use_container_width=True):
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_sales_logs, sales_deduction_map = [], {}
                    
                    for _, row in df_sales_raw.iterrows():
                        icode = str(row[match_code]).strip()
                        iname = str(row[match_name]).strip()
                        qty = float(row[match_qty])
                        
                        new_sales_logs.append([str(row[match_date]), icode, iname, "Sales", -qty, str(row[match_vouch]).strip(), timestamp_str])
                        sales_deduction_map[icode] = sales_deduction_map.get(icode, 0) + qty
                        
                    # Execute inventory dynamic deductions
                    updated_stock = df_stock.copy()
                    for code, qty_sold in sales_deduction_map.items():
                        if not updated_stock.empty and code in updated_stock["Item_Code"].values:
                            updated_stock.loc[updated_stock["Item_Code"] == code, "Current_Stock"] -= qty_sold
                        else:
                            new_row = pd.DataFrame([{"Item_Code": code, "Item_Name": "Unknown ERP Ingestion", "Current_Stock": -qty_sold, "ABC_Category": "C", "Avg_Daily_Sales": 0.0}])
                            updated_stock = pd.concat([updated_stock, new_row], ignore_index=True)
                    
                    # Temporarily append logs to feed accurate calculation formulas
                    temp_log_df = pd.concat([df_log, pd.DataFrame(new_sales_logs, columns=df_log.columns)], ignore_index=True)
                    
                    # Recompute Pareto metrics dynamically
                    updated_stock = recalculate_abc_and_velocity(updated_stock, temp_log_df)
                    
                    # Back up modified array tables down to cloud architecture sheets
                    ws_stock.clear()
                    ws_stock.append_rows([updated_stock.columns.tolist()] + updated_stock.fillna("").astype(str).values.tolist())
                    ws_log.append_rows(new_sales_logs)
                    ws_batches.append_rows([[sales_batch_id, "Sales", timestamp_str]])
                    
                    st.success("Sales ledger deducted! ABC Matrix distributions refreshed.")
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- MASTER INVENTORY DISPATCH REPORT GRID ---
st.markdown("### 📜 Real-Time Master Stock Ledger & Operational Velocity")

if df_stock.empty:
    st.info("📌 Stock Ledger Blank. Use Admin interfaces to upload opening warehouse balances or process MRN entries.")
else:
    # Color indicators based on ABC priority classification configurations
    def color_abc(val):
        if val == "A": return "🟩 Fast (A)"
        elif val == "B": return "🟨 Medium (B)"
        return "🟥 Slow (C)"
        
    df_stock_display = df_stock.copy()
    df_stock_display["ABC_Category"] = df_stock_display["ABC_Category"].apply(color_abc)
    
    st.dataframe(
        df_stock_display.sort_values(by="Current_Stock", ascending=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Item_Code": st.column_config.TextColumn("Item Code"),
            "Item_Name": st.column_config.TextColumn("Product Specification / Name"),
            "Current_Stock": st.column_config.NumberColumn("Current On-Hand Balance", format="%d Units"),
            "ABC_Category": st.column_config.TextColumn("ABC Class (Rolling 30d Volume)"),
            "Avg_Daily_Sales": st.column_config.NumberColumn("Daily Run-Rate Velocity", format="%.2f Units/Day 📈"),
            "Days_of_Coverage": st.column_config.NumberColumn("Available Days of Coverage", format="%d Days ⏳")
        }
    )
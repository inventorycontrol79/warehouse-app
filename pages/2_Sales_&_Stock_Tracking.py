import streamlit as st
import pandas as pd
import json
import gspread
import io  
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="SABIN PLASTIC // Inventory Intelligence", layout="wide")

# --- MULTI-PAGE ADMIN PERSISTENCE GATEWAY ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

url_params = st.query_params
if url_params.get("key", "") == "sabin_inventory":
    st.session_state.is_admin = True

is_admin = st.session_state.is_admin

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
    .admin-box { background-color: #1E1B4B; border: 1px solid #4338CA; border-radius: 8px; padding: 20px; margin-top: 20px; }
    
    div[data-testid="stRadio"] > label { display: none; }
    div[data-testid="stRadio"] div[role="radiogroup"] { gap: 10px; }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background-color: #111827;
        border: 1px solid #1E293B;
        padding: 8px 16px;
        border-radius: 20px;
        color: #94A3B8;
        transition: all 0.2s ease-in-out;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        border-color: #0EA5E9;
        color: #F8FAFC;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"][data-checked="true"] {
        background-color: #0EA5E9 !important;
        border-color: #0EA5E9 !important;
        color: #0B0F19 !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='premium-header'><div class='sabin-logo'>SABIN <span>PLASTIC</span></div><div class='sabin-sub'>Enterprise Warehouse Tracking System</div></div>", unsafe_allow_html=True)

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

@st.cache_resource(ttl=3600)
def get_worksheets():
    gc = get_google_client()
    if not gc: return None, None, None, None
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        return sh.get_worksheet(3), sh.get_worksheet(4), sh.get_worksheet(5), sh.get_worksheet(6)
    except Exception as e:
        st.error(f"🚨 Sheet Connection Failed: {e}")
        return None, None, None, None

@st.cache_data(ttl=300)
def load_data_from_sheet(ws_index, fallback_cols):
    try:
        gc = get_google_client()
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        ws = sh.get_worksheet(ws_index)
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=fallback_cols)
    except Exception:
        return pd.DataFrame(columns=fallback_cols)

def run_automatic_archiver(ws_log, ws_archive, df_log_current):
    if df_log_current.empty: return
    df_log_current["Timestamp_Parsed"] = pd.to_datetime(df_log_current["Timestamp"], errors='coerce')
    cutoff_date = datetime.now() - timedelta(days=45)
    
    df_to_keep = df_log_current[df_log_current["Timestamp_Parsed"] >= cutoff_date]
    df_to_archive = df_log_current[df_log_current["Timestamp_Parsed"] < cutoff_date]
    
    if not df_to_archive.empty:
        df_to_keep = df_to_keep.drop(columns=["Timestamp_Parsed"])
        df_to_archive = df_to_archive.drop(columns=["Timestamp_Parsed"])
        ws_archive.append_rows(df_to_archive.fillna("").astype(str).values.tolist())
        ws_log.clear()
        ws_log.append_rows([df_to_keep.columns.tolist()] + df_to_keep.fillna("").astype(str).values.tolist())
        st.toast(f"📦 Performance Boost: Moved {len(df_to_archive)} historical logs to data archive tab.", icon="♻️")

ws_stock, ws_log, ws_batches, ws_archive = get_worksheets()

# Explicit schema definitions including background velocity parameters
TARGET_STOCK_COLS = [
    "Item_Code", "Item_Name", "Product_Category", "Current_Stock",
    "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi",
    "ABC_Category", "Avg_Daily_Sales", "Last_Sold_Date", "Days_of_Coverage",
    "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"
]

df_stock = load_data_from_sheet(3, TARGET_STOCK_COLS)
df_log = load_data_from_sheet(4, ["Date", "Item_Code", "Item_Name", "Transaction_Type", "Qty_Delta", "Voucher_Reference", "Timestamp", "Branch"])
df_batches = load_data_from_sheet(5, ["Batch_ID", "Upload_Type", "Timestamp"])

# Dynamically patch structural columns if missing
for col in TARGET_STOCK_COLS:
    if col not in df_stock.columns:
        df_stock[col] = 0.0 if "Velocity" in col or "Stock" in col or col == "Avg_Daily_Sales" else ""

for d in [df_stock, df_log, df_batches]:
    if not d.empty:
        for col in d.columns:
            if d[col].dtype == 'object': d[col] = d[col].astype(str).str.strip()

# --- SIDEBAR INTERACTIVE FILTERS ---
st.sidebar.markdown("### ⚙️ INVENTORY FILTER")
if not df_stock.empty:
    df_stock["Product_Category"] = df_stock["Product_Category"].replace("", "Uncategorized").fillna("Uncategorized")
    cat_options = ["All Categories"] + sorted(df_stock["Product_Category"].unique().tolist())
else:
    cat_options = ["All Categories"]
selected_category_filter = st.sidebar.selectbox("Filter by Material Group", cat_options)
item_search = st.sidebar.text_input("🔍 Search Item Code / Description")

filt_stock = df_stock.copy()
if not filt_stock.empty and selected_category_filter != "All Categories":
    filt_stock = filt_stock[filt_stock["Product_Category"] == selected_category_filter]

if item_search:
    filt_stock = filt_stock[
        filt_stock["Item_Code"].str.contains(item_search, case=False, na=False) | 
        filt_stock["Item_Name"].str.contains(item_search, case=False, na=False)
    ]

# --- UPGRADED BACKGROUND MULTI-LOCATION VELOCITY ENGINE ---
def recalculate_abc_and_velocity(stock_df, log_df):
    if log_df.empty or stock_df.empty: return stock_df
    stock_df["Current_Stock"] = pd.to_numeric(stock_df["Current_Stock"], errors='coerce').fillna(0)
    log_df["Qty_Delta"] = pd.to_numeric(log_df["Qty_Delta"], errors='coerce').fillna(0)
    log_df["Timestamp"] = pd.to_datetime(log_df["Timestamp"], errors='coerce')
    
    if "Branch" not in log_df.columns:
        log_df["Branch"] = ""

    thirty_days_ago = datetime.now() - timedelta(days=30)
    sales_30 = log_df[(log_df["Transaction_Type"] == "Sales") & (log_df["Timestamp"] >= thirty_days_ago)]
    
    # Initialize background metrics safely
    for b_col in ["Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"]:
        stock_df[b_col] = 0.0

    if sales_30.empty:
        stock_df["ABC_Category"] = "C"
        stock_df["Avg_Daily_Sales"] = 0.0
        return stock_df
        
    # 1. Company Global Velocity Calculation Layer
    item_sales = sales_30.groupby("Item_Code")["Qty_Delta"].sum().reset_index()
    item_sales["Qty_Delta"] = item_sales["Qty_Delta"].abs()
    item_sales = item_sales.sort_values(by="Qty_Delta", ascending=False)
    
    total_volume = item_sales["Qty_Delta"].sum()
    item_sales["Cum_Percentage"] = item_sales["Qty_Delta"].cumsum() / total_volume if total_volume > 0 else 1.0
        
    def assign_abc(pct):
        if pct <= 0.80: return "A"
        elif pct <= 0.95: return "B"
        return "C"
        
    item_sales["ABC_Category"] = item_sales["Cum_Percentage"].apply(assign_abc)
    item_sales["Avg_Daily_Sales"] = round(item_sales["Qty_Delta"] / 30, 2)
    
    stock_df.set_index("Item_Code", inplace=True)
    item_sales.set_index("Item_Code", inplace=True)
    stock_df.update(item_sales[["ABC_Category", "Avg_Daily_Sales"]])
    stock_df.reset_index(inplace=True)

    # 2. Under-the-Hood Location Segment Mapping Loop
    branch_mappings = {
        "Dubai": "Velocity_Al_Quoz",
        "Sharjah": "Velocity_Sharjah",
        "DIP": "Velocity_DIP",
        "Abu Dhabi": "Velocity_Abu_Dhabi"
    }

    for branch_keyword, v_column in branch_mappings.items():
        sub_sales = sales_30[sales_30["Branch"].str.contains(branch_keyword, case=False, na=False)]
        if not sub_sales.empty:
            b_sales = sub_sales.groupby("Item_Code")["Qty_Delta"].sum().abs().reset_index()
            b_sales[v_column] = round(b_sales["Qty_Delta"] / 30, 2)
            
            stock_df.set_index("Item_Code", inplace=True)
            b_sales.set_index("Item_Code", inplace=True)
            stock_df.update(b_sales[[v_column]])
            stock_df.reset_index(inplace=True)

    stock_df["ABC_Category"] = stock_df["ABC_Category"].fillna("C")
    stock_df["Avg_Daily_Sales"] = pd.to_numeric(stock_df["Avg_Daily_Sales"], errors='coerce').fillna(0.0)
    return stock_df

if not df_stock.empty:
    df_stock["Current_Stock"] = pd.to_numeric(df_stock["Current_Stock"], errors='coerce').fillna(0)
    df_stock["Avg_Daily_Sales"] = pd.to_numeric(df_stock["Avg_Daily_Sales"], errors='coerce').fillna(0.0)
    df_stock["Days_of_Coverage"] = df_stock.apply(lambda r: 999 if r["Avg_Daily_Sales"] <= 0 else round(r["Current_Stock"] / r["Avg_Daily_Sales"], 1), axis=1)

filt_stock = df_stock.copy()
if not filt_stock.empty and selected_category_filter != "All Categories":
    filt_stock = filt_stock[filt_stock["Product_Category"] == selected_category_filter]

# --- SNAPSHOT KPIS SUMMARY ---
st.markdown(f"### 📊 Inventory Summary: {selected_category_filter}")
ninety_days_ago_str = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

total_skus = len(filt_stock) if not filt_stock.empty else 0
if not filt_stock.empty:
    stockout_count = len(filt_stock[(filt_stock["ABC_Category"] == "A") & (filt_stock["Days_of_Coverage"] <= 7)])
    a_count = len(filt_stock[filt_stock["ABC_Category"] == "A"])
    dead_stock_mask = (filt_stock["Last_Sold_Date"] < ninety_days_ago_str) | (filt_stock["Last_Sold_Date"] == "") | (filt_stock["Last_Sold_Date"].isna())
    overstock_count = len(filt_stock[dead_stock_mask])
else:
    stockout_count = overstock_count = a_count = 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("SKU COUNT IN FILTER", total_skus)
kpi2.metric("FAST MOVING (CLASS A)", a_count)
kpi3.metric("STOCKOUT RISK (<7 DAYS)", stockout_count, delta="Check Class A", delta_color="inverse")
kpi4.metric("DEAD STOCK (>90 DAYS NO SALE)", overstock_count, delta="Check Inactive", delta_color="off")

st.markdown(" ")
segment_view = st.radio(
    "Filter Grid Segment View:",
    options=["📋 Show All Rows", "🟩 Fast Moving Only (Class A)", "🚨 High Risk Only (<7 Days Coverage)", "📉 Dead Stock Only (>90 Days Inactive)"],
    horizontal=True
)

if segment_view == "🟩 Fast Moving Only (Class A)":
    filt_stock = filt_stock[filt_stock["ABC_Category"] == "A"]
elif segment_view == "🚨 High Risk Only (<7 Days Coverage)":
    filt_stock = filt_stock[(filt_stock["ABC_Category"] == "A") & (filt_stock["Days_of_Coverage"] <= 7)]
elif segment_view == "📉 Dead Stock Only (>90 Days Inactive)":
    filt_stock = filt_stock[(filt_stock["Last_Sold_Date"] < ninety_days_ago_str) | (filt_stock["Last_Sold_Date"] == "") | (filt_stock["Last_Sold_Date"].isna())]

if item_search:
    filt_stock = filt_stock[
        filt_stock["Item_Code"].astype(str).str.contains(item_search, case=False, na=False) | 
        filt_stock["Item_Name"].astype(str).str.contains(item_search, case=False, na=False)
    ]

st.markdown("---")

# --- FILE INGESTION CONTROLS (GATED) ---
if not is_admin:
    st.info("🔒 Stock adjustments and data ingestion engines locked. Displaying running terminal logs in read-only mode.")
else:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("<div class='upload-box'><h5>📥 Process Incoming Stock (MRN / Opening Balance)</h5>", unsafe_allow_html=True)
        mrn_file = st.file_uploader("Upload Inbound Excel (.xlsx)", type=["xlsx"], key="mrn_loader")
        if mrn_file:
            df_mrn_raw = pd.read_excel(mrn_file, engine="openpyxl")
            df_mrn_raw.columns = [str(c).strip() for c in df_mrn_raw.columns]
            req_mrn = ["Date", "Document No.", "Item.Code", "Item.Name", "Quantity"]
            if all(c in df_mrn_raw.columns for c in req_mrn):
                unique_batch = str(df_mrn_raw["Document No."].iloc[0]).strip()
                if not df_batches.empty and unique_batch in df_batches["Batch_ID"].values:
                    st.error(f"🛑 Double-Upload Blocked! Document Batch `{unique_batch}` has already been processed.")
                else:
                    if st.button("⚡ INTEGRATE INBOUND LOG INTO STOCK", use_container_width=True):
                        st.cache_data.clear()
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_logs, new_stock_map = [], {}
                        for _, row in df_mrn_raw.iterrows():
                            icode = str(row["Item.Code"]).strip()
                            iname = str(row["Item.Name"]).strip()
                            qty = float(row["Quantity"])
                            new_logs.append([str(row["Date"]), icode, iname, "MRN", qty, unique_batch, timestamp_str, "Central Log"])
                            new_stock_map[icode] = {"Item_Name": iname, "Qty": qty}
                        
                        updated_stock = df_stock.copy()
                        for code, info in new_stock_map.items():
                            if not updated_stock.empty and code in updated_stock["Item_Code"].values:
                                updated_stock.loc[updated_stock["Item_Code"] == code, "Current_Stock"] += info["Qty"]
                            else:
                                new_rows_data = {
                                    "Item_Code": code, "Item_Name": info["Item_Name"], "Product_Category": "Uncategorized", 
                                    "Current_Stock": info["Qty"], "ABC_Category": "C", "Avg_Daily_Sales": 0.0, "Last_Sold_Date": ""
                                }
                                for b_col in ["Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"]:
                                    new_rows_data[b_col] = 0.0
                                updated_stock = pd.concat([updated_stock, pd.DataFrame([new_rows_data])], ignore_index=True)
                                
                        ws_stock.clear()
                        ws_stock.append_rows([TARGET_STOCK_COLS] + updated_stock[TARGET_STOCK_COLS].fillna("").astype(str).values.tolist())
                        ws_log.append_rows(new_logs)
                        ws_batches.append_rows([[unique_batch, "MRN", timestamp_str]])
                        st.success(f"Inbound Sheet Data `{unique_batch}` incorporated successfully!")
                        st.rerun()
            else:
                st.error(f"Missing column fields. File must match format: {req_mrn}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("<div class='upload-box'><h5>📤 Process Outgoing Sales (Daily Ledger)</h5>", unsafe_allow_html=True)
        sales_file = st.file_uploader("Upload Yesterday's Sales Sheet (.xlsx)", type=["xlsx"], key="sales_loader")
        if sales_file:
            df_sales_raw = pd.read_excel(sales_file, engine="openpyxl")
            df_sales_raw.columns = [str(c).strip() for c in df_sales_raw.columns]
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
            # 🌟 NEW UPGRADE: Interactive Column selector for the Branch parameter layout
            match_branch = st.selectbox("Match Sales [Branch]:", cols, index=cols.index(find_col(["branch", "location", "warehouse"])))
            
            sales_batch_id = str(df_sales_raw[match_vouch].iloc[0]).strip() + "_SALES"
            if not df_batches.empty and sales_batch_id in df_batches["Batch_ID"].values:
                st.error("🛑 Double-Upload Blocked! This daily sales spreadsheet has already been deducted from inventory.")
            else:
                if st.button("⚡ EXECUTE QUANTITY DEDUCTION & ABC ANALYSIS", use_container_width=True):
                    st.cache_data.clear()
                    today_stamp = datetime.now().strftime("%Y-%m-%d")
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_sales_logs, sales_deduction_map = [], {}
                    
                    for _, row in df_sales_raw.iterrows():
                        icode = str(row[match_code]).strip()
                        iname = str(row[match_name]).strip()
                        qty = float(row[match_qty])
                        branch_val = str(row[match_branch]).strip()
                        
                        new_sales_logs.append([str(row[match_date]), icode, iname, "Sales", -qty, str(row[match_vouch]).strip(), timestamp_str, branch_val])
                        sales_deduction_map[icode] = sales_deduction_map.get(icode, 0) + qty
                        
                    updated_stock = df_stock.copy()
                    ignored_items_count = 0
                    filtered_sales_logs = []
                    
                    for code, qty_sold in sales_deduction_map.items():
                        if not updated_stock.empty and code in updated_stock["Item_Code"].values:
                            updated_stock.loc[updated_stock["Item_Code"] == code, "Current_Stock"] -= qty_sold
                            updated_stock.loc[updated_stock["Item_Code"] == code, "Last_Sold_Date"] = today_stamp
                        else:
                            ignored_items_count += 1
                            
                    for log_entry in new_sales_logs:
                        if log_entry[1] in updated_stock["Item_Code"].values:
                            filtered_sales_logs.append(log_entry)
                    
                    if ignored_items_count > 0:
                        st.warning(f"⚠️ Ignored {ignored_items_count} item(s) from the sales file because they do not exist in your Master Stock list.")
                        
                    if filtered_sales_logs:
                        temp_log_df = pd.concat([df_log, pd.DataFrame(filtered_sales_logs, columns=df_log.columns)], ignore_index=True)
                        updated_stock = recalculate_abc_and_velocity(updated_stock, temp_log_df)
                        
                        ws_stock.clear()
                        ws_stock.append_rows([TARGET_STOCK_COLS] + updated_stock[TARGET_STOCK_COLS].fillna("").astype(str).values.tolist())
                        ws_log.append_rows(filtered_sales_logs)
                        ws_batches.append_rows([[sales_batch_id, "Sales", timestamp_str]])
                        
                        st.success("Sales data successfully deducted and branch trends learned!")
                        st.rerun()
                    else:
                        st.error("❌ No items from this sales upload matched your Master Stock list. Zero adjustments recorded.")
        st.markdown("</div>", unsafe_allow_html=True)

# --- MASTER INVENTORY DISPATCH REPORT GRID ---
grid_header_col, download_btn_col = st.columns([3, 1])

with grid_header_col:
    st.markdown("### 📜 Material Segment Tracking Ledger")

def generate_professional_excel(dataframe, segment_name):
    output = io.BytesIO()
    clean_df = dataframe.copy()
    abc_map = {"A": "🟩 Class A (Fast)", "B": "🟨 Class B (Medium)", "C": "🟥 Class C (Slow)"}
    clean_df["ABC_Category"] = clean_df["ABC_Category"].map(abc_map).fillna("Unclassified")
    clean_df["Last_Sold_Date"] = clean_df["Last_Sold_Date"].replace("", "Never Tracked").fillna("Never Tracked")
    
    # Filter down to display columns only to keep executive export clean
    clean_df = clean_df[[
        "Item_Code", "Item_Name", "Product_Category", "Current_Stock", 
        "ABC_Category", "Avg_Daily_Sales", "Days_of_Coverage", "Last_Sold_Date"
    ]].rename(columns={
        "Item_Code": "Item Code",
        "Item_Name": "Product Specification / Description",
        "Product_Category": "Material Group",
        "Current_Stock": "Current Balance",
        "ABC_Category": "Velocity Classification",
        "Avg_Daily_Sales": "Daily Run-Rate Run Velocity",
        "Days_of_Coverage": "Estimated Days of Coverage",
        "Last_Sold_Date": "Last Active Dispatch Date"
    })
    
    clean_df = clean_df.sort_values(by="Current Balance", ascending=True)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        clean_df.to_excel(writer, sheet_name="Inventory Report", index=False, startrow=4)
        workbook = writer.book
        worksheet = writer.sheets["Inventory Report"]
        worksheet.views.sheetView[0].showGridLines = True
        
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        font_family = "Segoe UI"
        navy_header_fill = PatternFill(start_color="1B2A4A", end_color="1B2A4A", fill_type="solid")
        
        font_title = Font(name=font_family, size=16, bold=True, color="1B2A4A")
        font_subtitle = Font(name=font_family, size=10, italic=True, color="555555")
        font_headers = Font(name=font_family, size=11, bold=True, color="FFFFFF")
        font_data = Font(name=font_family, size=10)
        
        thin_side = Side(border_style="thin", color="D1D5DB")
        data_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        
        worksheet["A1"] = "SABIN PLASTIC // ENTERPRISE WAREHOUSE LEDGER"
        worksheet["A1"].font = font_title
        worksheet["A2"] = f"Material Segment Slice: {segment_name} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        worksheet["A2"].font = font_subtitle
        
        header_row = 5
        worksheet.row_dimensions[header_row].height = 26
        for col_idx in range(1, len(clean_df.columns) + 1):
            cell = worksheet.cell(row=header_row, column=col_idx)
            cell.fill = navy_header_fill
            cell.font = font_headers
            cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", vertical="center")
            cell.border = data_border
            
        for row_idx in range(6, len(clean_df) + 6):
            worksheet.row_dimensions[row_idx].height = 20
            for col_idx in range(1, len(clean_df.columns) + 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                cell.font = font_data
                cell.border = data_border
                
                if col_idx in [4, 6, 7]:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    if col_idx == 4: cell.number_format = '#,##0'
                    if col_idx == 6: cell.number_format = '#,##0.00'
                    if col_idx == 7: cell.number_format = '#,##0'
                elif col_idx in [1, 3, 5, 8]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    return output.getvalue()

with download_btn_col:
    if not filt_stock.empty:
        excel_data = generate_professional_excel(filt_stock, segment_view)
        st.download_button(
            label="📥 Download Excel Ledger",
            data=excel_data,
            file_name=f"Sabin_Inventory_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if filt_stock.empty:
    st.info("📌 No items found matching the selected segment filter criteria.")
    col_config_view = {}
else:
    def color_abc(val):
        if val == "A": return "🟩 Fast (A)"
        elif val == "B": return "🟨 Medium (B)"
        return "🟥 Slow (C)"
        
    df_stock_display = filt_stock.copy()
    df_stock_display["ABC_Category"] = df_stock_display["ABC_Category"].apply(color_abc)
    df_stock_display["Last_Sold_Date"] = df_stock_display["Last_Sold_Date"].replace("", "Never Tracked").fillna("Never Tracked")
    
    # Clean display views to keep out background math tracks from matrix grid view
    display_columns = [
        "Item_Code", "Item_Name", "Product_Category", "Current_Stock", 
        "ABC_Category", "Avg_Daily_Sales", "Days_of_Coverage", "Last_Sold_Date"
    ]
    
    st.dataframe(
        df_stock_display[display_columns].sort_values(by="Current_Stock", ascending=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Item_Code": st.column_config.TextColumn("Item Code"),
            "Item_Name": st.column_config.TextColumn("Product Specification / Description"),
            "Product_Category": st.column_config.TextColumn("Material Group"),
            "Current_Stock": st.column_config.NumberColumn("Current Balance", format="%d Units"),
            "ABC_Category": st.column_config.TextColumn("ABC Class (30d Sales Vol)"),
            "Avg_Daily_Sales": st.column_config.NumberColumn("Daily Velocity Run-Rate", format="%.2f Units/Day 📈"),
            "Days_of_Coverage": st.column_config.NumberColumn("Estimated Days of Coverage", format="%d Days ⏳"),
            "Last_Sold_Date": st.column_config.TextColumn("Last Dispatched Activity Date")
        }
    )

if is_admin and not df_stock.empty:
    uncat_items = df_stock[df_stock["Product_Category"] == "Uncategorized"]
    if not uncat_items.empty:
        st.markdown("<div class='admin-box'>⚙️ <b>Autonomous Intelligence Gateway: Assign Categories</b>", unsafe_allow_html=True)
        st.info(f"The system has detected **{len(uncat_items)}** unique item(s) currently marked as `Uncategorized` from your uploads. Assign them below to map your workspace permanently.")
        
        known_cats = sorted(list(set(df_stock["Product_Category"].unique()) - {"Uncategorized"}))
        target_row = uncat_items.iloc[0]
        st.warning(f"**Target Code:** `{target_row['Item_Code']}` | **Specification:** `{target_row['Item_Name']}`")
        
        assign_col1, assign_col2 = st.columns(2)
        with assign_col1:
            chosen_existing = st.selectbox("Assign to an Existing Material Group:", ["-- Create Completely New --"] + known_cats)
        with assign_col2:
            custom_new_cat = st.text_input("Or Type a Brand New Category Name (e.g., Rods, Adhesives, Mirror Sheet):")
            
        if st.button("💾 SAVE CATEGORIZATION ASSIGNMENT", use_container_width=True):
            st.cache_data.clear()
            final_cat_selection = custom_new_cat.strip() if chosen_existing == "-- Create Completely New --" and custom_new_cat.strip() != "" else chosen_existing
            
            if final_cat_selection in ["-- Create Completely New --", ""]:
                st.error("Please enter or choose a valid target category label before clicking update.")
            else:
                df_stock.loc[df_stock["Item_Code"] == target_row["Item_Code"], "Product_Category"] = final_cat_selection
                ws_stock.clear()
                ws_stock.append_rows([TARGET_STOCK_COLS] + df_stock[TARGET_STOCK_COLS].fillna("").astype(str).values.tolist())
                st.success(f"Item `{target_row['Item_Code']}` mapped to `{final_cat_selection}`! Re-indexing terminal framework...")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
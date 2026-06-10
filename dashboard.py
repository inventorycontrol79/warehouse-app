import streamlit as st
import pandas as pd
import altair as alt
import io
import os
import json
import gspread
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Command Center", layout="wide")

BOT_STATUS_FILE = "bot_status.txt"

# Auto-refresh system every 30 seconds to fetch live data updates
st_autorefresh(interval=30000, key="auto_refresh")

# --- PREMIUM HIGH-CONTRAST ERP STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    
    .stApp {
        background-color: #0B0F19; 
        color: #E2E8F0;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p {
        color: #F8FAFC !important;
    }
    
    label, .stWidgetLabel p {
        color: #94A3B8 !important;
        font-weight: 600 !important;
    }
    
    .premium-header {
        border-bottom: 1px solid #1E293B;
        padding-bottom: 1.5rem;
        margin-bottom: 2rem;
        margin-top: 1rem;
    }
    .sabin-logo {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: 4px;
        color: #F8FAFC !important;
        margin: 0;
        line-height: 1.2;
    }
    .sabin-logo span {
        color: #0EA5E9 !important; 
    }
    .sabin-sub {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 3px;
        color: #94A3B8 !important; 
        text-transform: uppercase;
        margin-top: 4px;
    }

    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1E293B;
        border-top: 3px solid #0EA5E9; 
        border-radius: 6px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #38BDF8;
    }
    .stMetric-value { 
        color: #F8FAFC !important; 
        font-size: 32px !important; 
        font-weight: 600 !important; 
    }
    .stMetric-label { 
        color: #94A3B8 !important; 
        font-size: 12px !important; 
        font-weight: 600 !important; 
        letter-spacing: 1px; 
        text-transform: uppercase;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] h4, 
    section[data-testid="stSidebar"] label {
        color: #F8FAFC !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER BARS ---
st.markdown("""
    <div class='premium-header'>
        <div class='sabin-logo'>SABIN <span>PLASTIC</span></div>
        <div class='sabin-sub'>Enterprise Warehouse Tracking System</div>
    </div>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CORE ENGINE ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    creds = json.loads(st.secrets["GOOGLE_JSON_STR"])
    return gspread.service_account_from_dict(creds)

def load_inventory_from_sheets():
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        
        # Access the first worksheet
        worksheet = sh.get_worksheet(0)
        
        data = worksheet.get_all_records(expected_headers=["DO_Number","Last_4","Status","Date_Issued","Warehouse_Name","Remarks","Created_By","Last_Modified"])
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return pd.DataFrame()

def save_inventory_to_sheets(dataframe):
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(0)
        
        # Clear and overwrite with new data
        worksheet.clear()
        
        # Ensure formatting for date column
        df_to_save = dataframe.copy()
        if "Date_Issued" in df_to_save.columns:
            df_to_save["Date_Issued"] = df_to_save["Date_Issued"].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
            )
            
        rows = [df_to_save.columns.tolist()] + df_to_save.fillna("").astype(str).values.tolist()
        worksheet.append_rows(rows)
        return True
    except Exception as e:
        st.error(f"🚨 Save Error: {e}")
        return False
# Load Base Data
df = load_inventory_from_sheets()

# Clean Data & Enforce Types
if not df.empty:
    df.columns = [str(c).strip() for c in df.columns]
    for col in ["DO_Number", "Warehouse_Name", "Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
    if "Date_Issued" in df.columns:
        df["Date_Issued"] = pd.to_datetime(df["Date_Issued"], format="%d/%m/%Y", errors="coerce")

# --- LIVE DIAGNOSTICS DISPLAY PANEL ---
st.markdown("### 🔍 SYSTEM DIAGNOSTICS")
col_diag1, col_diag2 = st.columns(2)
with col_diag1:
    st.metric("Rows Read From Cloud", len(df))
with col_diag2:
    st.write("Headers Found:", df.columns.tolist() if not df.empty else "NO HEADERS FOUND")

# --- ADVANCED URL PARAMETER ROUTING ENGINE ---
url_params = st.query_params
url_warehouse = url_params.get("warehouse", None)

if url_warehouse:
    url_warehouse = url_warehouse.strip()

is_supervisor_session = False
if url_warehouse and not df.empty and "Warehouse_Name" in df.columns and url_warehouse in df["Warehouse_Name"].unique():
    is_supervisor_session = True

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### ⚙️ SYSTEM CONTROLS")

if is_supervisor_session:
    st.sidebar.info("🔒 Administrative operations locked. Core ledger modifications are read-only for your terminal role.")
else:
    uploaded = st.sidebar.file_uploader("Upload Raw ERP Excel File", type=["xlsx"])

    if uploaded is not None:
        raw_erp = pd.read_excel(uploaded, engine="openpyxl")
        available_cols = [str(col).strip() for col in raw_erp.columns]
        raw_erp.columns = available_cols 
        
        st.sidebar.markdown("#### 🗺️ Align ERP Columns")
        
        def auto_match(possibilities, options):
            for p in possibilities:
                for opt in options:
                    if p.lower() in opt.lower():
                        return opt
            return options[0] if options else ""
        
        guess_do = auto_match(["voucher", "do number", "do_no", "invoice", "document", "delivery"], available_cols)
        guess_date = auto_match(["date", "issued", "time", "posting"], available_cols)
        guess_wh = auto_match(["godown", "warehouse", "location", "facility", "branch", "site"], available_cols)
        guess_user = auto_match(["created by", "user", "operator", "creator", "entered"], available_cols)
        
        chosen_do = st.sidebar.selectbox("Match [DO Number]:", available_cols, index=available_cols.index(guess_do) if guess_do in available_cols else 0)
        chosen_date = st.sidebar.selectbox("Match [Date Issued]:", available_cols, index=available_cols.index(guess_date) if guess_date in available_cols else 0)
        chosen_wh = st.sidebar.selectbox("Match [Warehouse]:", available_cols, index=available_cols.index(guess_wh) if guess_wh in available_cols else 0)
        chosen_user = st.sidebar.selectbox("Match [Created By]:", available_cols, index=available_cols.index(guess_user) if guess_user in available_cols else 0)
        
        if st.sidebar.button("⚡ EXECUTE PIPELINE ALIGNMENT"):
            new_df = pd.DataFrame({
                "DO_Number": raw_erp[chosen_do].astype(str).str.replace("DLNS:","", regex=False).str.strip(),
                "Date_Issued": pd.to_datetime(raw_erp[chosen_date], errors="coerce"),
                "Warehouse_Name": raw_erp[chosen_wh].astype(str).str.strip(),
                "Created_By": raw_erp[chosen_user].astype(str).str.strip()
            })

            new_df["Last_4"] = new_df["DO_Number"].str[-4:]
            new_df["Status"] = "Pending"
            new_df["Remarks"] = ""
            new_df["Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            combined = pd.concat([df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=["DO_Number"], keep="last", inplace=True)
            
            if save_inventory_to_sheets(combined):
                st.sidebar.success("Cloud Google Sheet synchronized successfully!")
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 Data Filters")

search = st.sidebar.text_input("🔍 Global DO Search")

if is_supervisor_session:
    warehouse_options = [url_warehouse]
    st.sidebar.markdown(f"📦 **Facility Bound:** `{url_warehouse}`")
else:
    warehouse_options = ["All"]
    if not df.empty and "Warehouse_Name" in df.columns:
        warehouse_options += sorted(df["Warehouse_Name"].astype(str).unique().tolist())

warehouse = st.sidebar.selectbox("🏭 Filter Facility", warehouse_options)
status = st.sidebar.selectbox("🏷️ Filter Status", ["All","Pending","Dispatched","Return"])

# --- DATE FILTER LOGIC ---
if not df.empty and "Date_Issued" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Date_Issued"]):
    min_date = df["Date_Issued"].min().date()
    max_date = df["Date_Issued"].max().date()
else:
    min_date = datetime.today().date()
    max_date = datetime.today().date()

# UI Date Picker
date_range = st.sidebar.date_input("📅 Filter Date Range", value=(min_date, max_date))

st.sidebar.markdown("---")
if os.path.exists(BOT_STATUS_FILE):
    try:
        ts = open(BOT_STATUS_FILE).read().strip()
        last = datetime.strptime(ts,"%Y-%m-%d %H:%M:%S")
        diff = (datetime.now()-last).total_seconds()
        if diff < 120:
            st.sidebar.success("🟢 API: Active & Routing")
        else:
            st.sidebar.error("🔴 API: Connection Lost")
    except:
        st.sidebar.warning("API Status: Unknown")
else:
    st.sidebar.info("🤖 API: Standby Mode")

# --- CENTRAL PIPELINE FILTER LOGIC ---
filt = df.copy()

if not filt.empty and len(filt.columns) >= 4:
    # 1. Global Search Filter
    if search:
        mask = filt.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        filt = filt[mask]
        
    # 2. Warehouse Filter
    if warehouse != "All" and "Warehouse_Name" in filt.columns: 
        filt = filt[filt["Warehouse_Name"] == warehouse]
        
    # 3. Status Filter
    if status != "All" and "Status" in filt.columns: 
        filt = filt[filt["Status"] == status]
        
    # 4. Date Range Filter
    if len(date_range) == 2 and "Date_Issued" in filt.columns:
        start_date, end_date = date_range
        filt = filt[(filt["Date_Issued"].dt.date >= start_date) & (filt["Date_Issued"].dt.date <= end_date)]
    elif len(date_range) == 1 and "Date_Issued" in filt.columns:
        # If user only selects a single day instead of a range
        start_date = date_range[0]
        filt = filt[filt["Date_Issued"].dt.date == start_date]

# --- EXECUTIVE METRIC CARDS ---
has_valid_data = not filt.empty and "Status" in filt.columns

total = len(filt) if not filt.empty else 0
dispatched = len(filt[filt["Status"]=="Dispatched"]) if has_valid_data else 0
pending = len(filt[filt["Status"]=="Pending"]) if has_valid_data else 0
returned = len(filt[filt["Status"]=="Return"]) if has_valid_data else 0

dispatch_rate = round((dispatched/total)*100,1) if total else 0

if has_valid_data and "Date_Issued" in filt.columns:
    pending_only = filt[filt["Status"] == "Pending"]
    try:
        valid_dates = pending_only[pending_only["Date_Issued"].notna()]
        avg_age = round(((pd.Timestamp.today() - valid_dates["Date_Issued"]).dt.days).mean(), 1) if not valid_dates.empty else 0
    except:
        avg_age = 0
else:
    pending_only = pd.DataFrame()
    avg_age = 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("TOTAL DO", total)
c2.metric("DISPATCHED", dispatched)
c3.metric("PENDING", pending)
c4.metric("RETURNS", returned)
c5.metric("DISPATCH %", f"{dispatch_rate}%")
c6.metric("AVG PENDING AGE", f"{avg_age} Days")

st.markdown("###")

if filt.empty or len(filt.columns) < 4:
    st.info("📌 System Online: No records match the sidebar filters, or sheet data requires initialization.")
else:
    # --- EXECUTIVE VISUALIZATIONS ---
    left, right = st.columns([1,1])

    with left:
        st.markdown("##### Distribution Pipeline")
        chart_df = pd.DataFrame({"Status":["Pending","Dispatched","Return"], "Count":[pending,dispatched,returned]})
        chart = alt.Chart(chart_df).mark_arc(innerRadius=80).encode(
            theta="Count:Q",
            color=alt.Color("Status:N", scale=alt.Scale(domain=["Pending","Dispatched","Return"], range=["#EAB308","#10B981","#EF4444"])),
            tooltip=["Status","Count"]
        ).properties(height=350, background="transparent").configure_view(stroke=None)
        st.altair_chart(chart, use_container_width=True)

    with right:
        st.markdown("##### Facility Workload Leaderboard")
        if "Warehouse_Name" in filt.columns and "DO_Number" in filt.columns:
            warehouse_summary = filt.groupby("Warehouse_Name").agg(Total=("DO_Number","count")).reset_index().sort_values("Total", ascending=False)
            st.dataframe(warehouse_summary, use_container_width=True, hide_index=True)

    if not pending_only.empty and "Date_Issued" in pending_only.columns:
        st.markdown("---")
        st.markdown("##### Critical Ageing Queue (Pending Orders Only)")
        try:
            pending_only_dates = pending_only[pending_only["Date_Issued"].notna()].copy()
            if not pending_only_dates.empty:
                pending_only_dates["Age_Days"] = (pd.Timestamp.today() - pending_only_dates["Date_Issued"]).dt.days
                def risk(x):
                    if x >= 6: return "🔴 High Risk"
                    elif x >= 3: return "🟡 Attention"
                    return "🟢 Standard"
                pending_only_dates["Risk_Profile"] = pending_only_dates["Age_Days"].apply(risk)
                display_cols = [c for c in ["DO_Number","Warehouse_Name","Age_Days","Risk_Profile"] if c in pending_only_dates.columns]
                st.dataframe(pending_only_dates[display_cols].sort_values("Age_Days", ascending=False), use_container_width=True, hide_index=True)
        except:
            pass

    # --- LIVE OPERATIONS INTERACTIVE LEDGER ---
    st.markdown("---")
    st.markdown("##### Active Operations Ledger")
    
    display_filt = filt.copy()
    if "Date_Issued" in display_filt.columns:
        try:
            display_filt["Date_Issued"] = display_filt["Date_Issued"].dt.strftime('%d/%m/%Y')
        except:
            pass
    
    disabled_cols = [c for c in ["DO_Number", "Last_4", "Date_Issued", "Warehouse_Name", "Created_By", "Last_Modified"] if c in display_filt.columns]
    grid_disabled_setting = True if is_supervisor_session else disabled_cols

    edited = st.data_editor(
        display_filt,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Pending","Dispatched","Return"])
        },
        disabled=grid_disabled_setting
    )

    if not is_supervisor_session:
        if st.button("💾 COMMIT RECORD TO DATABASE"):
            base = load_inventory_from_sheets()
            if not base.empty and "DO_Number" in base.columns:
                base["DO_Number"] = base["DO_Number"].astype(str).str.strip()
                for _, row in edited.iterrows():
                    do = str(row["DO_Number"]).strip()
                    if "Status" in row:
                        base.loc[base["DO_Number"] == do, "Status"] = row["Status"]
                    if "Remarks" in row:
                        base.loc[base["DO_Number"] == do, "Remarks"] = row["Remarks"]
                    base.loc[base["DO_Number"] == do, "Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if save_inventory_to_sheets(base):
                    st.success("System database overwritten successfully! Reloading canvas matrix...")
                    st.rerun()

    # --- EXECUTIVE EXCEL SECURED REPORT ENGINE ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        summary_df = pd.DataFrame({"Metric":["Total DO","Dispatched","Pending","Return","Dispatch %"], "Value":[total,dispatched,pending,returned,f"{dispatch_rate}%"]})
        summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)
        
        excel_filt = filt.copy()
        if "Date_Issued" in excel_filt.columns:
            try:
                excel_filt["Date_Issued"] = excel_filt["Date_Issued"].dt.strftime('%d/%m/%Y')
            except:
                pass
        excel_filt.to_excel(writer, sheet_name="Dispatch Records", index=False)
        
        wb = writer.book
        header = wb.add_format({"bold":True, "bg_color":"#0F172A", "font_color":"white"})
        
        for sheet in ["Executive Summary","Dispatch Records"]:
            ws = writer.sheets[sheet]
            ws.freeze_panes(1,0)
            cols = summary_df.columns if sheet == "Executive Summary" else excel_filt.columns
            for col_num, value in enumerate(cols):
                ws.write(0, col_num, value, header)
                ws.set_column(col_num, col_num, 20)

    st.markdown("###")
    st.download_button("📥 DOWNLOAD SECURE LEDGER (XLSX)", buffer.getvalue(), "SABIN_Enterprise_Logistics.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
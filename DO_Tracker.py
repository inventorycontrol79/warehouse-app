import streamlit as st
import pandas as pd
import altair as alt
import io
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Command Center", layout="wide")
BOT_STATUS_FILE = "bot_status.txt"

# Modern background polling interval (30 Seconds)
st_autorefresh(interval=30000, key="auto_refresh")

# --- SECRET KEY ADMIN ACCESS GATEWAY ---
url_params = st.query_params
# Strict structural verification for your personal secret key
is_admin = url_params.get("key", "") == "sabin_inventory"

# --- PREMIUM HIGH-CONTRAST ERP STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #94A3B8 !important; font-weight: 600 !important; }
    
    /* Branding Header Components */
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 12px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    
    /* Industrial Grade KPI Card Containers */
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1E293B; border-top: 3px solid #0EA5E9; border-radius: 6px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.2s ease; }
    div[data-testid="metric-container"]:hover { border-color: #38BDF8; transform: translateY(-2px); }
    .stMetric-value { color: #F8FAFC !important; font-size: 32px !important; font-weight: 600 !important; }
    .stMetric-label { color: #94A3B8 !important; font-size: 12px !important; font-weight: 600 !important; letter-spacing: 1px; text-transform: uppercase; }
    
    /* Sidebar Overrides */
    section[data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid #1E293B; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4, section[data-testid="stSidebar"] label { color: #F8FAFC !important; }
    
    /* Form Wrapper Module Cards */
    .action-card { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class='premium-header'>
        <div class='sabin-logo'>SABIN <span>PLASTIC</span></div>
        <div class='sabin-sub'>Enterprise Warehouse Tracking System</div>
    </div>
""", unsafe_allow_html=True)

# --- NATIVE AUTHENTICATION & SHEET CONNECTION ENGINE ---
def get_google_sheet_connection():
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        return gc.open_by_url(st.secrets["GSHEET_URL"])
    except Exception as e:
        st.error(f"🚨 Authentication Failed: {e}")
        return None

def load_inventory_from_sheets():
    sh = get_google_sheet_connection()
    if not sh: return pd.DataFrame()
    try:
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Last_4","Status","Date_Issued","Warehouse_Name","Remarks","Created_By","Last_Modified"])
    except Exception as e:
        st.error(f"🛑 Error reading main sheet: {e}")
        return pd.DataFrame()

def load_historical_returns_log():
    sh = get_google_sheet_connection()
    if not sh: return pd.DataFrame()
    try:
        data = sh.get_worksheet(2).get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Voucher_Number","Return_Date","Match_Status","Return_Type","Return_Remarks","Logged_By","Timestamp"])
    except Exception as e:
        return pd.DataFrame()

def save_inventory_to_sheets(dataframe):
    sh = get_google_sheet_connection()
    if not sh: return False
    try:
        worksheet = sh.get_worksheet(0)
        worksheet.clear()
        headers = dataframe.columns.tolist()
        df_to_save = dataframe.copy()
        
        if "Date_Issued" in df_to_save.columns:
            df_to_save["Date_Issued"] = df_to_save["Date_Issued"].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
            )
        rows = df_to_save.fillna("").astype(str).values.tolist()
        worksheet.append_rows([headers] + rows)
        return True
    except Exception as e:
        st.error(f"🚨 Main Data backup failed: {e}")
        return False

# --- STATE AND CACHE REFRESH CONTROL LAYER ---
if "master_data" not in st.session_state:
    st.session_state.master_data = pd.DataFrame()
if "last_fetch_time" not in st.session_state:
    st.session_state.last_fetch_time = None

current_time = datetime.now()
if st.session_state.master_data.empty or st.session_state.last_fetch_time is None or (current_time - st.session_state.last_fetch_time).total_seconds() >= 30:
    fetched_df = load_inventory_from_sheets()
    if not fetched_df.empty:
        st.session_state.master_data = fetched_df
        st.session_state.last_fetch_time = current_time

df = st.session_state.master_data.copy()
if not df.empty:
    df["DO_Number"] = df["DO_Number"].astype(str).str.strip()
    df["Warehouse_Name"] = df["Warehouse_Name"].astype(str).str.strip()
    df["Date_Issued"] = pd.to_datetime(df["Date_Issued"], format="%d/%m/%Y", errors="coerce")

# --- PARAMETER ROUTING SECURITY ---
url_warehouse = url_params.get("warehouse", None)
if url_warehouse: url_warehouse = url_warehouse.strip()
is_supervisor_session = True if url_warehouse and not df.empty and url_warehouse in df["Warehouse_Name"].unique() else False

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### ⚙️ SYSTEM CONTROLS")

# Secure Admin Gate for Raw ERP Excel Upload Logic
if not is_admin:
    st.sidebar.info("🔒 Administrative pipeline locked. Ledger modifications are running in read-only terminal mode.")[cite: 2]
elif is_supervisor_session:
    st.sidebar.warning("🔒 Supervisor profile bound. File uploading interface suspended.")
else:
    uploaded = st.sidebar.file_uploader("Upload Raw ERP Excel File", type=["xlsx"])
    if uploaded is not None:
        raw_erp = pd.read_excel(uploaded, engine="openpyxl")
        available_cols = [str(col).strip() for col in raw_erp.columns]
        raw_erp.columns = available_cols 
        
        def auto_match(possibilities, options):
            for p in possibilities:
                for opt in options:
                    if p.lower() in opt.lower(): return opt
            return options[0] if options else ""
        
        guess_do = auto_match(["voucher", "do number", "do_no", "invoice", "document", "delivery"], available_cols)
        guess_date = auto_match(["date", "issued", "time", "posting"], available_cols)
        guess_wh = auto_match(["godown", "warehouse", "location", "facility", "branch", "site"], available_cols)
        guess_user = auto_match(["created by", "user", "operator", "creator", "entered"], available_cols)
        
        chosen_do = st.sidebar.selectbox("Match [DO Number]:", available_cols, index=available_cols.index(guess_do) if guess_do in available_cols else 0)
        chosen_date = st.sidebar.selectbox("Match [Date Issued]:", available_cols, index=available_cols.index(guess_date) if guess_date in available_cols else 0)
        chosen_wh = st.sidebar.selectbox("Match [Warehouse]:", available_cols, index=available_cols.index(guess_wh) if guess_wh in available_cols else 0)
        chosen_user = st.sidebar.selectbox("Match [Created By]:", available_cols, index=available_cols.index(guess_user) if guess_user in available_cols else 0)
        
        if st.sidebar.button("⚡ EXECUTE PIPELINE ALIGNMENT", use_container_width=True):
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

            df_returns_hist = load_historical_returns_log()
            if not df_returns_hist.empty:
                df_returns_hist["DO_Number"] = df_returns_hist["DO_Number"].astype(str).str.strip()
                matched_returns = df_returns_hist[df_returns_hist["DO_Number"].isin(new_df["DO_Number"].tolist())]
                
                if not matched_returns.empty:
                    st.sidebar.warning(f"🔄 Auto-Reconciliation Engine: Intercepted {len(matched_returns)} retroactive returns!")
                    for _, ret_row in matched_returns.iterrows():
                        r_do = str(ret_row["DO_Number"]).strip()
                        r_type = str(ret_row["Return_Type"]).strip()
                        r_rem = str(ret_row["Return_Remarks"]).strip()
                        
                        new_df.loc[new_df["DO_Number"] == r_do, "Status"] = "Return"
                        new_df.loc[new_df["DO_Number"] == r_do, "Remarks"] = f"[{r_type}] {r_rem} (Retro-Reconciled)"

            combined = pd.concat([df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=["DO_Number"], keep="last", inplace=True)
            
            if save_inventory_to_sheets(combined):
                st.session_state.master_data = pd.DataFrame()
                st.session_state.last_fetch_time = None
                st.sidebar.success("Live Sheet synchronized successfully!")
                st.rerun()

search = st.sidebar.text_input("🔍 Global DO Search")

if is_supervisor_session:
    warehouse_options = [url_warehouse]
    st.sidebar.markdown(f"📦 **Facility Bound:** `{url_warehouse}`")
else:
    warehouse_options = ["All"] + sorted(df["Warehouse_Name"].astype(str).unique().tolist()) if not df.empty else ["All"]

warehouse = st.sidebar.selectbox("Filter Facility", warehouse_options)
status = st.sidebar.selectbox("Filter Status", ["All","Pending","Dispatched","Return"])

if not df.empty and pd.notna(df["Date_Issued"].min()):
    min_date, max_date = df["Date_Issued"].min().date(), df["Date_Issued"].max().date()
else:
    min_date = max_date = datetime.today().date()

st.sidebar.markdown("### 📅 TIMEFRAME")
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)

st.sidebar.markdown("---")
if os.path.exists(BOT_STATUS_FILE):
    try:
        ts = open(BOT_STATUS_FILE).read().strip()
        if (datetime.now() - datetime.strptime(ts,"%Y-%m-%d %H:%M:%S")).total_seconds() < 120:
            st.sidebar.success("🟢 API: Active & Routing")
        else:
            st.sidebar.error("🔴 API: Connection Lost")
    except: st.sidebar.warning("API Status: Unknown")
else: st.sidebar.info("🤖 API: Standby Mode")

# --- CENTRAL PIPELINE FILTER LOGIC ---
filt = df.copy()
if not filt.empty:
    if search: 
        filt = filt[filt["DO_Number"].str.contains(search, case=False, na=False) | filt["Warehouse_Name"].str.contains(search, case=False, na=False)]
    if warehouse != "All": filt = filt[filt["Warehouse_Name"] == warehouse]
    if status != "All": filt = filt[filt["Status"] == status]
    filt = filt[(filt["Date_Issued"].dt.date >= start_date) & (filt["Date_Issued"].dt.date <= end_date)]

# --- EXECUTIVE SUMMARY METRICS ---
total = len(filt) if not filt.empty else 0
dispatched = len(filt[filt["Status"]=="Dispatched"]) if not filt.empty else 0
pending = len(filt[filt["Status"]=="Pending"]) if not filt.empty else 0
returned = len(filt[filt["Status"]=="Return"]) if not filt.empty else 0
dispatch_rate = round((dispatched/total)*100,1) if total else 0
avg_age = round(((pd.Timestamp.today() - filt[filt["Status"] == "Pending"]["Date_Issued"]).dt.days).mean(), 1) if not filt.empty and not filt[filt["Status"] == "Pending"].empty else 0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("TOTAL DO", total)
m2.metric("DISPATCHED", dispatched)
m3.metric("PENDING", pending)
m4.metric("RETURNS", returned)
m5.metric("DISPATCH %", f"{dispatch_rate}%")
m6.metric("AVG PENDING AGE", f"{avg_age} Days")

# --- LOGISTICS ARCHIVE EXPANDER MODULE (ADMIN SECURED) ---
if is_admin and not is_supervisor_session:
    st.markdown("###")
    with st.expander("💼 LOGISTICS DATA ARCHIVE MODULE", expanded=False):
        arc_col1, arc_col2, arc_col3 = st.columns([2, 2, 3])
        with arc_col1: arc_start = st.date_input("Archive Threshold Start", value=min_date, key="arch_start_input")
        with arc_col2: arc_end = st.date_input("Archive Threshold End", value=datetime.today().date(), key="arch_end_input")
        to_archive = df[(df["Date_Issued"].dt.date >= arc_start) & (df["Date_Issued"].dt.date <= arc_end) & (df["Status"].isin(["Dispatched", "Return"]))] if not df.empty else pd.DataFrame()
        with arc_col3:
            st.markdown(f"<div style='padding-top:1.5rem;'>📦 Archive Target Records Found: <b>{len(to_archive)} rows</b></div>", unsafe_allow_html=True)
        
        if not to_archive.empty:
            if st.button("⚡ EXECUTE SECURE MIGRATION TO COLD STORAGE", use_container_width=True):
                sh = get_google_sheet_connection()
                if sh:
                    try:
                        archive_sheet = sh.get_worksheet(1)
                        df_export = to_archive.copy()
                        df_export["Date_Issued"] = df_export["Date_Issued"].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x))
                        archive_sheet.append_rows(df_export.fillna("").astype(str).values.tolist())
                        
                        if save_inventory_to_sheets(df.drop(to_archive.index)):
                            st.session_state.master_data = pd.DataFrame()
                            st.session_state.last_fetch_time = None
                            st.success("Archive Transfer Completed!")
                            st.rerun()
                    except Exception as ex: st.error(f"Archive processing error: {ex}")

if filt.empty:
    st.info("📌 System Online: Waiting for Cloud synchronized interface link connection.")
else:
    left, right = st.columns([1,1])
    with left:
        st.markdown("##### Distribution Pipeline Breakdown")
        chart_df = pd.DataFrame({"Status":["Pending","Dispatched","Return"], "Count":[pending,dispatched,returned]})
        chart = alt.Chart(chart_df).mark_arc(innerRadius=80).encode(
            theta="Count:Q", 
            color=alt.Color("Status:N", scale=alt.Scale(domain=["Pending","Dispatched","Return"], range=["#EAB308","#10B981","#EF4444"])), 
            tooltip=["Status","Count"]
        ).properties(height=280, background="transparent").configure_view(stroke=None)
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.markdown("##### Facility Workload Leaderboard")
        leaderboard_df = filt.groupby("Warehouse_Name").agg(Total=("DO_Number","count")).reset_index().sort_values("Total", ascending=False)
        st.dataframe(leaderboard_df, use_container_width=True, hide_index=True, height=280)

    # --- PENDING ORDERS AGEING BREAKDOWN ---
    st.markdown("---")
    st.markdown("##### ⏳ Pending Orders Ageing Breakdown")
    
    pending_df = filt[filt["Status"] == "Pending"].copy()
    if pending_df.empty:
        st.success("🟢 Outstanding Backlog Cleared: No pending orders detected within current filters.")
    else:
        today_ts = pd.Timestamp(datetime.now().date())
        pending_df["Days_Open"] = (today_ts - pending_df["Date_Issued"]).dt.days
        
        def assign_bucket_details(days):
            if days <= 3: return "0 - 3 Days (Normal)", "🟢 Normal"
            elif days <= 7: return "4 - 7 Days (Warning)", "🟡 Warning"
            elif days <= 14: return "8 - 14 Days (Critical)", "🟠 Critical"
            else: return "15+ Days (Severely Overdue)", "🔴 Overdue"
            
        bucket_res = pending_df["Days_Open"].apply(assign_bucket_details)
        pending_df["Ageing_Bucket"] = [r[0] for r in bucket_res]
        pending_df["Risk_Level"] = [r[1] for r in bucket_res]
        
        st.markdown("<div style='font-size: 13px; color: #94A3B8; margin-bottom: 10px;'>Use the filters below to pinpoint exactly which orders are stuck:</div>", unsafe_allow_html=True)
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            all_b_options = ["All Buckets", "0 - 3 Days (Normal)", "4 - 7 Days (Warning)", "8 - 14 Days (Critical)", "15+ Days (Severely Overdue)"]
            selected_bucket = st.selectbox("Filter by Age Category", all_b_options, key="age_bucket_filter")
            
        with f_col2:
            all_w_options = ["All Locations"] + sorted(pending_df["Warehouse_Name"].unique().tolist())
            selected_wh = st.selectbox("Filter by Pending Location", all_w_options, key="age_wh_filter")
            
        drill_df = pending_df.copy()
        if selected_bucket != "All Buckets":
            drill_df = drill_df[drill_df["Ageing_Bucket"] == selected_bucket]
        if selected_wh != "All Locations":
            drill_df = drill_df[drill_df["Warehouse_Name"] == selected_wh]
            
        drill_df = drill_df.sort_values(by="Days_Open", ascending=False)
        drill_df["Formatted_Date"] = drill_df["Date_Issued"].dt.strftime('%d/%m/%Y')
        display_drill = drill_df[["DO_Number", "Formatted_Date", "Warehouse_Name", "Days_Open", "Risk_Level", "Remarks"]]
        
        st.markdown(f"📋 Showing **{len(display_drill)}** outstanding order(s) matching selection:")
        st.dataframe(
            display_drill,
            use_container_width=True,
            hide_index=True,
            column_config={
                "DO_Number": st.column_config.TextColumn("DO Number"),
                "Formatted_Date": st.column_config.TextColumn("Date Issued"),
                "Warehouse_Name": st.column_config.TextColumn("Warehouse Location"),
                "Days_Open": st.column_config.NumberColumn("Days Stagnant", format="%d Days Pending ⏳"),
                "Risk_Level": st.column_config.TextColumn("Risk Status"),
                "Remarks": st.column_config.TextColumn("Operational Notes")
            }
        )

    # --- LIVE OPERATIONS INTERACTIVE LEDGER (GATED) ---
    st.markdown("---")
    st.markdown("##### Active Operations Ledger")
    
    display_filt = filt.copy()
    display_filt["Date_Issued"] = display_filt["Date_Issued"].dt.strftime('%d/%m/%Y')
    
    # Grid input locking mechanism triggers if session lacks valid credentials or matches supervisor profile constraints
    grid_disabled = True if (is_supervisor_session or not is_admin) else ["DO_Number", "Last_4", "Date_Issued", "Warehouse_Name", "Created_By", "Last_Modified"][cite: 2]
    
    edited = st.data_editor(
        display_filt, 
        use_container_width=True, 
        hide_index=True, 
        column_config={
            "DO_Number": st.column_config.TextColumn("DO Number"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Pending","Dispatched","Return"], required=True),
            "Remarks": st.column_config.TextColumn("Operational Notes & Exceptions"),
            "Last_Modified": st.column_config.TextColumn("System Timestamp", disabled=True)
        }, 
        disabled=grid_disabled
    )

    # Secure Gated Action Trigger Button
    if is_admin and not is_supervisor_session:
        if st.button("💾 COMMIT RECORD TO DATABASE", type="primary", use_container_width=True):
            base = load_inventory_from_sheets()
            if not base.empty:
                base["DO_Number"] = base["DO_Number"].astype(str).str.strip()
                timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for _, row in edited.iterrows():
                    do_target = str(row["DO_Number"]).strip()
                    base.loc[base["DO_Number"] == do_target, "Status"] = row["Status"]
                    base.loc[base["DO_Number"] == do_target, "Remarks"] = row["Remarks"]
                    base.loc[base["DO_Number"] == do_target, "Last_Modified"] = timestamp_now
                    
                if save_inventory_to_sheets(base):
                    st.session_state.master_data = pd.DataFrame()
                    st.session_state.last_fetch_time = None
                    st.success("Database overwritten successfully!")
                    st.rerun()

    # --- SECURE DATA EXPORT ENGINE ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        pd.DataFrame({
            "Metric": ["Total DO","Dispatched","Pending","Return","Dispatch %", "Average Pending Age"], 
            "Value": [total, dispatched, pending, returned, f"{dispatch_rate}%", f"{avg_age} Days"]
        }).to_excel(writer, sheet_name="Executive Summary", index=False)
        
        excel_filt = filt.copy()
        excel_filt["Date_Issued"] = excel_filt["Date_Issued"].dt.strftime('%d/%m/%Y')
        excel_filt.to_excel(writer, sheet_name="Dispatch Records", index=False)
        
    st.markdown("###")
    st.download_button("📥 DOWNLOAD SECURE LEDGER (XLSX)", buffer.getvalue(), "SABIN_Enterprise_Logistics.xlsx", use_container_width=True)[cite: 2]
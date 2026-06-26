import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="SABIN PLASTIC // Returns Engine", layout="wide")

# --- MULTI-PAGE ADMIN PERSISTENCE GATEWAY ---
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Evaluate URL query strings in case they refresh directly on this engine page
url_params = st.query_params
if url_params.get("key", "") == "sabin_inventory":
    st.session_state.is_admin = True

# Read authority privileges from persistent memory
is_admin = st.session_state.is_admin

# High-Contrast Premium Dark Theme Style Overrides
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
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1E293B; border-top: 3px solid #EF4444; border-radius: 6px; padding: 20px; }
    .action-card { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
    .conflict-box { background: linear-gradient(90deg, #1E1B4B 0%, #111827 100%); border-left: 4px solid #EAB308; border-radius: 6px; padding: 15px; margin-bottom: 12px; }
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

def load_inventory_from_sheets():
    gc = get_google_client()
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        data = sh.get_worksheet(0).get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Last_4","Status","Date_Issued","Warehouse_Name","Remarks","Created_By","Last_Modified"])
    except Exception as e:
        st.error(f"🛑 Error reading main sheet: {e}")
        return pd.DataFrame()

def load_historical_returns_log():
    gc = get_google_client()
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        data = sh.get_worksheet(2).get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Voucher_Number","Return_Date","Match_Status","Return_Type","Return_Remarks","Logged_By","Timestamp"])
    except Exception as e:
        return pd.DataFrame()

def save_inventory_to_sheets(dataframe):
    gc = get_google_client()
    if not gc: return False
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(0)
        worksheet.clear()
        headers = dataframe.columns.tolist()
        df_to_save = dataframe.copy()
        if "Date_Issued" in df_to_save.columns:
            df_to_save["Date_Issued"] = df_to_save["Date_Issued"].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x))
        worksheet.append_rows([headers] + df_to_save.fillna("").astype(str).values.tolist())
        return True
    except Exception as e:
        st.error(f"🚨 Main Data backup failed: {e}")
        return False

def log_returns_to_archive_sheet(return_rows):
    gc = get_google_client()
    if not gc: return False
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        sh.get_worksheet(2).append_rows(return_rows)
        return True
    except Exception as e:
        st.error(f"🚨 Failed logging returns to cloud archive: {e}")
        return False

# Load Datasets
df_master = load_inventory_from_sheets()
if not df_master.empty:
    df_master["DO_Number"] = df_master["DO_Number"].astype(str).str.strip()
df_returns_history = load_historical_returns_log()

# Live Metrics Snapshot Computation
st.markdown("### 📊 Return Operations Snapshot")
yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
total_historic = len(df_returns_history) if not df_returns_history.empty else 0

if not df_returns_history.empty:
    df_returns_history["Return_Date"] = df_returns_history["Return_Date"].astype(str).str.strip()
    yesterday_returns = df_returns_history[df_returns_history["Return_Date"] == yesterday_str]
    total_yesterday = len(yesterday_returns)
    full_yesterday = len(yesterday_returns[yesterday_returns["Return_Type"] == "Full"])
    partial_yesterday = len(yesterday_returns[yesterday_returns["Return_Type"] == "Partial"])
else:
    total_yesterday = full_yesterday = partial_yesterday = 0

m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("Processed (Yesterday)", f"{total_yesterday} DOs")
with m2: st.metric("Full Returns (Yesterday)", f"{full_yesterday} Orders")
with m3: st.metric("Partial Returns (Yesterday)", f"{partial_yesterday} Flagged")
with m4: st.metric("All-Time Logged Archive", f"{total_historic} Total Records")

st.markdown("---")
st.markdown("## 📥 Sales Return Intake Engine")

# Gated Verification for Sheet Uploader Widget
if not is_admin:
    st.info("🔒 Return submission engine locked. Please use authorized terminal paths to commit database write variations.")
else:
    uploaded_return = st.file_uploader("Upload ERP Sales Return Sheet (.xlsx)", type=["xlsx"], key="return_upload_unique")
    if uploaded_return is not None:
        ret_df = pd.read_excel(uploaded_return, engine="openpyxl")
        ret_df.columns = [str(c).strip() for c in ret_df.columns]
        ret_cols = ret_df.columns.tolist()
        
        def match_ret(queries, options):
            for q in queries:
                for o in options:
                    if q.lower() in o.lower(): return o
            return options[0] if options else ""
            
        sel_do = st.selectbox("Confirm Return [DO Number] Column:", ret_cols, index=ret_cols.index(match_ret(["do number", "do_no", "delivery order"], ret_cols)))
        sel_vouch = st.selectbox("Confirm Sales [Voucher / Invoice Number] Column:", ret_cols, index=ret_cols.index(match_ret(["invoice no", "invoice_no", "voucher", "sales number"], ret_cols)))
        sel_date = st.selectbox("Confirm Return [Date] Column:", ret_cols, index=ret_cols.index(match_ret(["date", "posting"], ret_cols)))
        sel_user = st.selectbox("Confirm Return [Operator] Column:", ret_cols, index=ret_cols.index(match_ret(["created by", "user"], ret_cols)))
        
        if st.button("🔍 RUN RECONCILIATION SCAN", use_container_width=True):
            clean_dos = ret_df[sel_do].astype(str).str.replace("DLNS:", "", case=False, regex=False).str.strip()
            cleaned_returns = pd.DataFrame({
                "DO_Number": clean_dos,
                "Voucher_Number": ret_df[sel_vouch].astype(str).str.strip(),
                "Return_Date": pd.to_datetime(ret_df[sel_date], errors="coerce").dt.strftime('%d/%m/%Y'),
                "Logged_By": ret_df[sel_user].astype(str).str.strip()
            }).dropna(subset=["DO_Number"]).drop_duplicates(subset=["DO_Number"])
            cleaned_returns = cleaned_returns[cleaned_returns["DO_Number"] != ""]
            
            active_dos = df_master["DO_Number"].tolist() if not df_master.empty else []
            conflicts, standards = [], []
            
            for _, r in cleaned_returns.iterrows():
                target_do = str(r["DO_Number"]).strip()
                vouch_no = str(r["Voucher_Number"]).strip()
                if target_do in active_dos:
                    curr_status = df_master[df_master["DO_Number"] == target_do]["Status"].values[0]
                    if curr_status in ["Pending", "Dispatched"]:
                        conflicts.append({"DO_Number": target_do, "Voucher_Number": vouch_no, "Return_Date": r["Return_Date"], "Current_Status": curr_status, "Return_Type": "Full", "Remarks": "", "Logged_By": r["Logged_By"]})
                        continue
                standards.append([target_do, vouch_no, r["Return_Date"], "Unmatched Backlog Return", "Full", "Awaiting Warehouse File Upload", r["Logged_By"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            
            st.session_state["detected_conflicts"] = conflicts
            st.session_state["detected_standards"] = standards
            st.success(f"Scan Finished! Found {len(conflicts)} Live Queue Conflicts and {len(standards)} Standard System Returns.")

    # Interactive Resolution Terminal Layout
    if "detected_conflicts" in st.session_state and st.session_state["detected_conflicts"]:
        st.markdown("---### ⚠️ ACTION REQUIRED: Active Ledger Conflicts Detected")
        updated_conflicts, all_valid = [], True
        
        for idx, item in enumerate(st.session_state["detected_conflicts"]):
            st.markdown(f"<div class='conflict-box'>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
            with col1:
                st.markdown(f"**DO Number:** `{item['DO_Number']}`")
                st.markdown(f"**Voucher No:** `{item['Voucher_Number']}`")
                st.markdown(f"Status: <span style='color:#0EA5E9;font-weight:bold;'>{item['Current_Status']}</span>", unsafe_allow_html=True)
            with col2:
                ret_type = st.radio(f"Return Type for {item['DO_Number']}", ["Full", "Partial"], key=f"type_{idx}_{item['DO_Number']}", horizontal=True)
            with col3:
                if ret_type == "Partial":
                    st.markdown("<span style='color:#EAB308; font-weight:bold;'>⚠️ REMARKS MANDATORY</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#10B981; font-weight:bold;'>🟢 READY FOR RESET</span>", unsafe_allow_html=True)
            with col4:
                rem_val = st.text_input(f"Operational Remarks for {item['DO_Number']}", value=item["Remarks"], key=f"rem_{idx}_{item['DO_Number']}")
            
            if ret_type == "Partial" and not rem_val.strip(): all_valid = False
            updated_conflicts.append({"DO_Number": item["DO_Number"], "Voucher_Number": item["Voucher_Number"], "Return_Date": item["Return_Date"], "Match_Status": "Active Ledger Conflict", "Return_Type": ret_type, "Return_Remarks": rem_val if rem_val.strip() else "Full Return Entry", "Logged_By": item["Logged_By"]})
            st.markdown("</div>", unsafe_allow_html=True)

        if not all_valid:
            st.error("🔒 Submission Locked: Provide a mandatory remark description for all Partial Returns to unlock database updates.")
        else:
            if st.button("⚡ POST RECONCILED DISPATCH VALUES", type="primary", use_container_width=True):
                base_ledger = load_inventory_from_sheets()
                archive_rows, timestamp_str = [], datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if not base_ledger.empty:
                    base_ledger["DO_Number"] = base_ledger["DO_Number"].astype(str).str.strip()
                    for c in updated_conflicts:
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Status"] = "Return"
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Remarks"] = f"[{c['Return_Type']}] " + c["Return_Remarks"]
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Last_Modified"] = timestamp_str
                        archive_rows.append([c["DO_Number"], c["Voucher_Number"], c["Return_Date"], c["Match_Status"], c["Return_Type"], c["Return_Remarks"], c["Logged_By"], timestamp_str])
                for s in st.session_state.get("detected_standards", []): archive_rows.append(s)
                if save_inventory_to_sheets(base_ledger) and log_returns_to_archive_sheet(archive_rows):
                    del st.session_state["detected_conflicts"], st.session_state["detected_standards"]
                    st.success("Perfect! System Overwritten.")
                    st.rerun()

    elif "detected_standards" in st.session_state and st.session_state["detected_standards"]:
        if st.button("⚡ COMMIT STANDARD RETURN LOGS", use_container_width=True):
            if log_returns_to_archive_sheet(st.session_state["detected_standards"]):
                del st.session_state["detected_standards"]
                st.rerun()

# Permanent Sales Returns Archive Ledger display (Always accessible to all viewers)
st.markdown("---")
st.markdown("### 📜 Permanent Sales Returns Archive Ledger")

if df_returns_history.empty:
    st.info("ℹ️ No historical return transactions logged inside cloud storage archive yet.")
else:
    if "Timestamp" in df_returns_history.columns:
        display_history = df_returns_history.sort_values(by="Timestamp", ascending=False)
    else:
        display_history = df_returns_history

    st.dataframe(
        display_history,
        use_container_width=True,
        hide_index=True,
        column_config={
            "DO_Number": st.column_config.TextColumn("DO Number"),
            "Voucher_Number": st.column_config.TextColumn("Voucher / Invoice Reference"),
            "Return_Date": st.column_config.TextColumn("ERP Posting Date"),
            "Match_Status": st.column_config.TextColumn("Validation Flag"),
            "Return_Type": st.column_config.TextColumn("Return Scope"),
            "Return_Remarks": st.column_config.TextColumn("Operational Exceptions / Notes"),
            "Logged_By": st.column_config.TextColumn("Authorized Operator"),
            "Timestamp": st.column_config.TextColumn("Database Commit Time")
        }
    )
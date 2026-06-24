import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Returns Engine", layout="wide")

# --- PREMIUM HIGH-CONTRAST ERP STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #94A3B8 !important; font-weight: 600 !important; }
    
    /* Header Branding */
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 12px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    
    /* Sidebar Dark Theme Alignment */
    section[data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] h4, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p { color: #F8FAFC !important; }
    
    /* Live Analytics Metric Cards styling */
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1E293B; border-top: 3px solid #0EA5E9; border-radius: 6px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .stMetric-value { color: #F8FAFC !important; font-size: 32px !important; font-weight: 600 !important; }
    .stMetric-label { color: #94A3B8 !important; font-size: 12px !important; font-weight: 600 !important; letter-spacing: 1px; text-transform: uppercase; }
    
    /* Premium UI Action Container boxes */
    .action-card { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class='premium-header'>
        <div class='sabin-logo'>SABIN <span>PLASTIC</span></div>
        <div class='sabin-sub'>Enterprise Warehouse Tracking System</div>
    </div>
""", unsafe_allow_html=True)

# --- NATIVE AUTHENTICATION ENGINE ---
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

# --- GOOGLE SHEETS STORAGE UTILITIES ---
def load_inventory_from_sheets():
    gc = get_google_client()
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Last_4","Status","Date_Issued","Warehouse_Name","Remarks","Created_By","Last_Modified"])
    except Exception as e:
        st.error(f"🛑 Error reading main sheet: {e}")
        return pd.DataFrame()

def load_historical_returns_log():
    gc = get_google_client()
    if not gc: return pd.DataFrame()
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(2) 
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["DO_Number","Return_Date","Match_Status","Return_Type","Return_Remarks","Logged_By","Timestamp"])
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
            df_to_save["Date_Issued"] = df_to_save["Date_Issued"].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
            )
        rows = df_to_save.fillna("").astype(str).values.tolist()
        worksheet.append_rows([headers] + rows)
        return True
    except Exception as e:
        st.error(f"🚨 Main Data backup failed: {e}")
        return False

def log_returns_to_archive_sheet(return_rows):
    gc = get_google_client()
    if not gc: return False
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(2)  
        worksheet.append_rows(return_rows)
        return True
    except Exception as e:
        st.error(f"🚨 Failed logging returns to cloud archive: {e}")
        return False

# --- LOAD LIVE DATA BASELINES ---
df_master = load_inventory_from_sheets()
if not df_master.empty:
    df_master["DO_Number"] = df_master["DO_Number"].astype(str).str.strip()

df_returns_history = load_historical_returns_log()

# --- SUPERVISOR URL PARSING SECURITY ---
url_params = st.query_params
url_warehouse = url_params.get("warehouse", None)
if url_warehouse: url_warehouse = url_warehouse.strip()
is_supervisor_session = True if url_warehouse and not df_master.empty and url_warehouse in df_master["Warehouse_Name"].unique() else False

# --- SYSTEM SUB-NAVIGATION TABS ---
tab_intake, tab_ledger = st.tabs(["📥 Return Reconcile Engine", "📜 Master Audit Archive"])

with tab_intake:
    st.markdown("### 📊 Return Operations Snapshot (Current Run)")

    # Dynamic KPI Calculations
    if "conflict_df" in st.session_state and "standard_df" in st.session_state:
        total_run = len(st.session_state["conflict_df"]) + len(st.session_state["standard_df"])
        conflicts_count = len(st.session_state["conflict_df"])
        standards_count = len(st.session_state["standard_df"])
    else:
        total_run = conflicts_count = standards_count = 0

    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Batch Detected", f"{total_run} Orders")
    with m2: st.metric("Active Ledger Conflicts", f"{conflicts_count} Requires Action")
    with m3: st.metric("Clean Pass-Throughs", f"{standards_count} Automated")

    st.markdown("---")

    if is_supervisor_session:
        st.warning("🔒 Access Denied: Sales return posting operations are restricted to corporate administrative terminals.")
    else:
        st.markdown("<div class='action-card'>", unsafe_allow_html=True)
        uploaded_return = st.file_uploader("Upload ERP Sales Return Sheet (.xlsx)", type=["xlsx"], key="return_upload_unique")
        st.markdown("</div>", unsafe_allow_html=True)
        
        if uploaded_return is not None:
            ret_df = pd.read_excel(uploaded_return, engine="openpyxl")
            ret_df.columns = [str(c).strip() for c in ret_df.columns]
            
            # Smart Target Mapping Alignment
            ret_cols = ret_df.columns.tolist()
            def match_ret(queries, options):
                for q in queries:
                    for o in options:
                        if q.lower() in o.lower(): return o
                return options[0] if options else ""
                
            c1, c2, c3, c4 = st.columns(4)
            with c1: sel_do = st.selectbox("DO Number Column:", ret_cols, index=ret_cols.index(match_ret(["invoice no", "invoice_no", "voucher", "do"], ret_cols)))
            with c2: sel_date = st.selectbox("Return Date Column:", ret_cols, index=ret_cols.index(match_ret(["date", "return", "posting"], ret_cols)))
            with c3: sel_user = st.selectbox("Operator Column:", ret_cols, index=ret_cols.index(match_ret(["created by", "created_by", "user", "operator"], ret_cols)))
            with c4: sel_reason = st.selectbox("Reason Column:", ret_cols, index=ret_cols.index(match_ret(["reason", "remark", "narration"], ret_cols)))
            
            if st.button("🔍 EXECUTE RECONCILIATION SCAN", type="primary", use_container_width=True):
                clean_dos = ret_df[sel_do].astype(str).str.replace("DLNS:", "", case=False, regex=False).str.strip()

                cleaned_returns = pd.DataFrame({
                    "DO_Number": clean_dos,
                    "Return_Date": pd.to_datetime(ret_df[sel_date], errors="coerce").dt.strftime('%d/%m/%Y'),
                    "Logged_By": ret_df[sel_user].astype(str).str.strip(),
                    "ERP_Reason": ret_df[sel_reason].astype(str).str.strip() if sel_reason in ret_cols else "Auto-extracted"
                }).dropna(subset=["DO_Number"]).drop_duplicates(subset=["DO_Number"])
                
                cleaned_returns = cleaned_returns[cleaned_returns["DO_Number"] != ""]
                active_dos = df_master["DO_Number"].tolist() if not df_master.empty else []
                
                conflicts = []
                standards = []
                
                for _, r in cleaned_returns.iterrows():
                    target_do = str(r["DO_Number"]).strip()
                    
                    # Double-Upload Shield
                    if not df_returns_history.empty:
                        already_processed = df_returns_history[
                            (df_returns_history["DO_Number"].astype(str) == target_do) & 
                            (df_returns_history["Timestamp"].astype(str).str.contains(datetime.now().strftime("%Y-%m-%d")))
                        ]
                        if not already_processed.empty:
                            continue
                    
                    extracted_remarks = r["ERP_Reason"] if str(r["ERP_Reason"]).strip() and str(r["ERP_Reason"]).lower() != "nan" else "Auto-extracted from ERP"
                    
                    if target_do in active_dos:
                        curr_status = df_master[df_master["DO_Number"] == target_do]["Status"].values[0]
                        if curr_status in ["Pending", "Dispatched"]:
                            conflicts.append({
                                "DO_Number": target_do, "Return_Date": r["Return_Date"],
                                "Current_Status": curr_status, "Return_Type": "Full", "Remarks": extracted_remarks, "Logged_By": r["Logged_By"]
                            })
                            continue
                    standards.append({
                        "DO_Number": target_do, "Return_Date": r["Return_Date"], "Match_Status": "Standard Return", 
                        "Return_Type": "Full", "Return_Remarks": extracted_remarks, "Logged_By": r["Logged_By"]
                    })
                
                st.session_state["conflict_df"] = pd.DataFrame(conflicts)
                st.session_state["standard_df"] = pd.DataFrame(standards)
                st.rerun()

        # --- INTERACTIVE EDITING MATRIX ---
        if "conflict_df" in st.session_state and not st.session_state["conflict_df"].empty:
            st.markdown("### ⚠️ Action Required: Active Ledger Conflicts")
            st.info("The following DO numbers exist in active dispatch pipelines. Review types and operational logs directly inside the grid below.")
            
            # Global Override Quick Tools
            b_col1, b_col2 = st.columns([2, 6])
            with b_col1:
                bulk_all_full = st.button("⚡ Quick-Set All Rows to Full Reversal")
                if bulk_all_full:
                    st.session_state["conflict_df"]["Return_Type"] = "Full"
                    st.rerun()
            
            # Interactive Premium Grid
            edited_df = st.data_editor(
                st.session_state["conflict_df"],
                column_config={
                    "DO_Number": st.column_config.TextColumn("DO Number", disabled=True),
                    "Return_Date": st.column_config.TextColumn("ERP Date", disabled=True),
                    "Current_Status": st.column_config.TextColumn("Live Pipeline Status", disabled=True),
                    "Return_Type": st.column_config.SelectboxColumn("Return Type", options=["Full", "Partial"], required=True),
                    "Remarks": st.column_config.TextColumn("Operational Remarks (Mandatory for Partial)"),
                    "Logged_By": st.column_config.TextColumn("Operator", disabled=True),
                },
                hide_index=True,
                use_container_width=True,
                key="conflict_editor"
            )
            
            # Guardrails validation checker
            partial_missing_remarks = edited_df[(edited_df["Return_Type"] == "Partial") & ((edited_df["Remarks"].str.strip() == "") | (edited_df["Remarks"] == "Auto-extracted from ERP"))]
            
            if not partial_missing_remarks.empty:
                st.error("🔒 Post Lockout: Operational details must be added in the remarks column for all 'Partial' returns.")
                st.button("⚡ TRANSMIT & PROCESS BALANCE DATA", disabled=True, use_container_width=True)
            else:
                if st.button("⚡ TRANSMIT & PROCESS BALANCE DATA", type="primary", use_container_width=True):
                    base_ledger = load_inventory_from_sheets()
                    archive_rows_to_append = []
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if not base_ledger.empty:
                        base_ledger["DO_Number"] = base_ledger["DO_Number"].astype(str).str.strip()
                        for _, c in edited_df.iterrows():
                            base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Status"] = "Return"
                            base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Remarks"] = f"[{c['Return_Type']}] " + c["Remarks"]
                            base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Last_Modified"] = timestamp_str
                            
                            archive_rows_to_append.append([c["DO_Number"], c["Return_Date"], "Active Ledger Conflict", c["Return_Type"], c["Remarks"], c["Logged_By"], timestamp_str])
                    
                    if "standard_df" in st.session_state and not st.session_state["standard_df"].empty:
                        for _, s in st.session_state["standard_df"].iterrows():
                            archive_rows_to_append.append([s["DO_Number"], s["Return_Date"], s["Match_Status"], s["Return_Type"], s["Return_Remarks"], s["Logged_By"], timestamp_str])
                    
                    if save_inventory_to_sheets(base_ledger):
                        if log_returns_to_archive_sheet(archive_rows_to_append):
                            st.session_state.master_data = pd.DataFrame()
                            st.session_state.last_fetch_time = None
                            del st.session_state["conflict_df"]
                            del st.session_state["standard_df"]
                            st.success("Perfect! System Overwritten. Active entries changed to 'Return' status and logs filed safely.")
                            st.rerun()

        elif "standard_df" in st.session_state and not st.session_state["standard_df"].empty:
            st.markdown("### 🟢 Clean Return Batches Identified")
            st.info(f"System identified **{len(st.session_state['standard_df'])}** standard returns clearing with zero active queue conflicts.")
            
            if st.button("⚡ COMMIT STANDARD RETURN LOGS ONLY", type="primary", use_container_width=True):
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                archive_rows_to_append = []
                for _, s in st.session_state["standard_df"].iterrows():
                    archive_rows_to_append.append([s["DO_Number"], s["Return_Date"], s["Match_Status"], s["Return_Type"], s["Return_Remarks"], s["Logged_By"], timestamp_str])
                
                if log_returns_to_archive_sheet(archive_rows_to_append):
                    del st.session_state["standard_df"]
                    st.success("Standard ledger logs successfully synchronized to cloud archive.")
                    st.rerun()

# --- HISTORICAL AUDIT MATRIX TAB ---
with tab_ledger:
    st.markdown("### 📜 Sales Return Master Ledger (Cloud Storage Archive)")
    if not df_returns_history.empty:
        # Mini Sidebar-style filtering within the main page context
        f_col1, f_col2 = st.columns([2, 6])
        with f_col1:
            search_query = st.text_input("🔍 Quick Query Filter (DO / Operator):", placeholder="Type to filter...")
        
        filtered_history = df_returns_history.copy()
        if search_query:
            filtered_history = filtered_history[
                filtered_history["DO_Number"].astype(str).str.contains(search_query) | 
                filtered_history["Logged_By"].astype(str).str.contains(search_query, case=False)
            ]

        st.dataframe(
            filtered_history.sort_values(by="Timestamp", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "DO_Number": st.column_config.TextColumn("DO Number"),
                "Return_Date": st.column_config.TextColumn("Return Date"),
                "Match_Status": st.column_config.TextColumn("Reconciliation Status"),
                "Return_Type": st.column_config.TextColumn("Type"),
                "Return_Remarks": st.column_config.TextColumn("Remarks / Details"),
                "Logged_By": st.column_config.TextColumn("Operator ID"),
                "Timestamp": st.column_config.TextColumn("Processed Time")
            }
        )
    else:
        st.info("No historical return records found in the archive sheet.")
import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Returns Intake", layout="wide")

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
        gc = gspread.authorize(creds)
        gc.open_by_url(st.secrets["GSHEET_URL"])
        return gc
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
        worksheet = sh.get_worksheet(2)  # Tab Index 2 (Sales_Returns)
        worksheet.append_rows(return_rows)
        return True
    except Exception as e:
        st.error(f"🚨 Failed logging returns to cloud archive: {e}")
        return False

# --- LOAD LIVE DATA BASELINE ---
df_master = load_inventory_from_sheets()
if not df_master.empty:
    df_master["DO_Number"] = df_master["DO_Number"].astype(str).str.strip()

# --- SUPERVISOR URL PARSING SECURITY ---
url_params = st.query_params
url_warehouse = url_params.get("warehouse", None)
if url_warehouse: url_warehouse = url_warehouse.strip()
is_supervisor_session = True if url_warehouse and not df_master.empty and url_warehouse in df_master["Warehouse_Name"].unique() else False

# --- ENGINE INTERFACE UI ---
st.markdown("## 📥 Sales Return Intake Engine")
st.markdown("Upload daily commercial return files to scan for operational delivery conflicts.")

if is_supervisor_session:
    st.warning("🔒 Access Denied: Sales return posting operations are restricted to corporate administrative terminals.")
else:
    uploaded_return = st.file_uploader("Upload ERP Sales Return Sheet (.xlsx)", type=["xlsx"], key="return_upload_unique")
    
    if uploaded_return is not None:
        ret_df = pd.read_excel(uploaded_return, engine="openpyxl")
        ret_df.columns = [str(c).strip() for c in ret_df.columns]
        
        st.markdown("### 🗺️ Target Mapping Alignment")
        ret_cols = ret_df.columns.tolist()
        
        def match_ret(queries, options):
            for q in queries:
                for o in options:
                    if q.lower() in o.lower(): return o
            return options[0] if options else ""
            
        sel_do = st.selectbox("Confirm Return [DO Number] Column:", ret_cols, index=ret_cols.index(match_ret(["voucher", "do", "delivery", "invoice"], ret_cols)))
        sel_date = st.selectbox("Confirm Return [Date] Column:", ret_cols, index=ret_cols.index(match_ret(["date", "return", "posting"], ret_cols)))
        sel_user = st.selectbox("Confirm Return [Operator] Column:", ret_cols, index=ret_cols.index(match_ret(["user", "created", "by", "operator"], ret_cols)))
        
        if st.button("🔍 RUN RECONCILIATION SCAN"):
            cleaned_returns = pd.DataFrame({
                "DO_Number": ret_df[sel_do].astype(str).str.replace("DLNS:","", regex=False).str.strip(),
                "Return_Date": pd.to_datetime(ret_df[sel_date], errors="coerce").dt.strftime('%d/%m/%Y'),
                "Logged_By": ret_df[sel_user].astype(str).str.strip()
            }).drop_duplicates(subset=["DO_Number"])
            
            active_dos = df_master["DO_Number"].tolist() if not df_master.empty else []
            conflicts = []
            standards = []
            
            for _, r in cleaned_returns.iterrows():
                if r["DO_Number"] in active_dos:
                    curr_status = df_master[df_master["DO_Number"] == r["DO_Number"]]["Status"].values[0]
                    if curr_status in ["Pending", "Dispatched"]:
                        conflicts.append({
                            "DO_Number": r["DO_Number"], "Return_Date": r["Return_Date"],
                            "Current_Status": curr_status, "Return_Type": "Full", "Remarks": "", "Logged_By": r["Logged_By"]
                        })
                        continue
                standards.append([r["DO_Number"], r["Return_Date"], "Standard Return", "Full", "Auto-logged", r["Logged_By"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            
            st.session_state["detected_conflicts"] = conflicts
            st.session_state["detected_standards"] = standards
            st.success(f"Scan Finished! Found {len(conflicts)} Live Queue Conflicts and {len(standards)} Standard System Returns.")

    # Display Interactive Conflict Matrix if populated
    if "detected_conflicts" in st.session_state and st.session_state["detected_conflicts"]:
        st.markdown("---")
        st.markdown("### ⚠️ ACTION REQUIRED: Active Ledger Conflicts Detected")
        st.info("The following DO numbers are currently flagged as Pending or Dispatched in your dashboard. You must specify if these returns are Full or Partial.")
        
        updated_conflicts = []
        all_valid = True
        
        for idx, item in enumerate(st.session_state["detected_conflicts"]):
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
                with col1:
                    st.markdown(f"**DO:** `{item['DO_Number']}`")
                    st.caption(f"Current Dashboard Status: **{item['Current_Status']}**")
                with col2:
                    ret_type = st.radio(f"Type for {item['DO_Number']}", ["Full", "Partial"], key=f"type_{idx}_{item['DO_Number']}")
                with col3:
                    st.markdown("<p style='margin-bottom:28px;'></p>", unsafe_allow_html=True)
                    if ret_type == "Partial":
                        st.markdown("⚠️ <span style='color:#EAB308; font-weight:bold;'>Remarks Required</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("🟢 <span style='color:#10B981;'>Ready</span>", unsafe_allow_html=True)
                with col4:
                    rem_val = st.text_input(f"Remarks / Details for {item['DO_Number']}", value=item["Remarks"], key=f"rem_{idx}_{item['DO_Number']}")
                
                if ret_type == "Partial" and not rem_val.strip():
                    all_valid = False
                    
                updated_conflicts.append({
                    "DO_Number": item["DO_Number"], "Return_Date": item["Return_Date"],
                    "Match_Status": "Active Ledger Conflict", "Return_Type": ret_type,
                    "Return_Remarks": rem_val if rem_val.strip() else "Full Return Entry", "Logged_By": item["Logged_By"]
                })
                st.markdown("<hr style='border: 0.5px solid #1E293B;'/>", unsafe_allow_html=True)

        if not all_valid:
            st.error("🔒 Submission Locked: You selected 'Partial' return for one or more orders. You must enter details in the remarks column before committing.")
            st.button("⚙️ POST RECONCILED DISPATCH VALUES", disabled=True)
        else:
            if st.button("⚡ POST RECONCILED DISPATCH VALUES", type="primary"):
                base_ledger = load_inventory_from_sheets()
                archive_rows_to_append = []
                timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if not base_ledger.empty:
                    base_ledger["DO_Number"] = base_ledger["DO_Number"].astype(str).str.strip()
                    for c in updated_conflicts:
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Status"] = "Return"
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Remarks"] = f"[{c['Return_Type']}] " + c["Return_Remarks"]
                        base_ledger.loc[base_ledger["DO_Number"] == c["DO_Number"], "Last_Modified"] = timestamp_str
                        
                        archive_rows_to_append.append([c["DO_Number"], c["Return_Date"], c["Match_Status"], c["Return_Type"], c["Return_Remarks"], c["Logged_By"], timestamp_str])
                
                for s in st.session_state.get("detected_standards", []):
                    archive_rows_to_append.append(s)
                    
                if save_inventory_to_sheets(base_ledger):
                    if log_returns_to_archive_sheet(archive_rows_to_append):
                        st.session_state.master_data = pd.DataFrame()
                        st.session_state.last_fetch_time = None
                        del st.session_state["detected_conflicts"]
                        del st.session_state["detected_standards"]
                        st.success("Perfect! Active entries changed to 'Return' status and logs filed safely.")
                        st.rerun()
                        
    elif "detected_standards" in st.session_state and st.session_state["detected_standards"]:
        st.markdown("---")
        st.markdown("### 🟢 Clean Return Batches Found")
        st.write(f"Detected **{len(st.session_state['detected_standards'])}** return items that have no active conflicts in the dispatch queue.")
        
        if st.button("⚡ COMMIT STANDARD RETURN LOGS"):
            if log_returns_to_archive_sheet(st.session_state["detected_standards"]):
                del st.session_state["detected_standards"]
                st.success("Standard records logged directly to cold-storage tab successfully.")
                st.rerun()
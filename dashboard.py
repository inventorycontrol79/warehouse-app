import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- SYSTEM CONFIGURATION & AUTO-REFRESH ---
st.set_page_config(page_title="SABIN PLASTIC // Command Center", layout="wide")
st_autorefresh(interval=30000, key="global_auto_refresh")

# --- PREMIUM CORPORATE HIGH-CONTRAST STYLING ---
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
    div[data-testid="metric-container"] { background-color: #111827; border: 1px solid #1E293B; border-top: 3px solid #0EA5E9; border-radius: 6px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    section[data-testid="stSidebar"] { background-color: #0F172A; border-right: 1px solid #1E293B; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class='premium-header'>
        <div class='sabin-logo'>SABIN <span>PLASTIC</span></div>
        <div class='sabin-sub'>Logistics Engine & Command Center Workspace</div>
    </div>
""", unsafe_allow_html=True)

# --- CLOUD DATABASE AUTHENTICATION ---
def get_google_client():
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 API Connection Error: {e}")
        return None

# --- SAFE DATAFRAME FETCH & CACHE ENGINE ---
def load_sheet_data(sheet_index, fallback_cols):
    gc = get_google_client()
    if not gc: return pd.DataFrame(columns=fallback_cols)
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(sheet_index)
        data = worksheet.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=fallback_cols)
    except Exception as e:
        st.error(f"🛑 Error loading Sheet Tab {sheet_index}: Please verify connection.")
        return pd.DataFrame(columns=fallback_cols)

def save_sheet_data(dataframe, sheet_index, date_col=None):
    gc = get_google_client()
    if not gc: return False
    try:
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        worksheet = sh.get_worksheet(sheet_index)
        worksheet.clear()
        
        headers = dataframe.columns.tolist()
        df_to_save = dataframe.copy()
        if date_col and date_col in df_to_save.columns:
            df_to_save[date_col] = df_to_save[date_col].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
            )
        rows = df_to_save.fillna("").astype(str).values.tolist()
        worksheet.append_rows([headers] + rows)
        return True
    except Exception as e:
        st.error(f"🚨 Cloud sync failed: {e}")
        return False

# --- FETCH DATA INTO STATE ---
fallback_fields = ["DO_Number","Last_4","Status","Date_Issued","Warehouse_Name","Remarks","Created_By","Last_Modified"]
if "dispatch_data" not in st.session_state or st.session_state.dispatch_data.empty:
    st.session_state.dispatch_data = load_sheet_data(0, fallback_fields)

df_dispatch = st.session_state.dispatch_data.copy()

# Ensure proper datetime parsing for date calculations
if not df_dispatch.empty:
    df_dispatch["Date_Issued"] = pd.to_datetime(df_dispatch["Date_Issued"], format="%d/%m/%Y", errors="coerce")

# ====================================================================
# ULTRA-EFFICIENT SIDEBAR MANAGEMENT CONTROLS
# ====================================================================
st.sidebar.markdown("### 🔍 CONTROL & FILTERS")
search_do = st.sidebar.text_input("Search Outgoing DO Number", placeholder="Type DO number...")

# Dynamically populate warehouse selection list safely
if not df_dispatch.empty and "Warehouse_Name" in df_dispatch.columns:
    wh_options = ["All"] + sorted(df_dispatch["Warehouse_Name"].dropna().unique().tolist())
else:
    wh_options = ["All"]
wh_filter = st.sidebar.selectbox("Filter Warehouse Hub", wh_options)
status_filter = st.sidebar.selectbox("Filter Queue Status", ["All", "Pending", "Dispatched", "Return"])

# Apply Interactive Pipeline Filtering
filt = df_dispatch.copy()
if search_do:
    filt = filt[filt["DO_Number"].astype(str).str.contains(search_do, case=False)]
if wh_filter != "All":
    filt = filt[filt["Warehouse_Name"] == wh_filter]
if status_filter != "All":
    filt = filt[filt["Status"] == status_filter]

# ====================================================================
# LIVE METRICS SUMMARY
# ====================================================================
st.subheader("Delivery Dispatch Status Tracking Queue")

c1, c2, c3, c4 = st.columns(4)
if not filt.empty:
    c1.metric("Total Active Load", len(filt))
    c2.metric("Pending Dispatch", len(filt[filt["Status"] == "Pending"]))
    c3.metric("Successfully Cleared", len(filt[filt["Status"] == "Dispatched"]))
    c4.metric("Flagged Returns", len(filt[filt["Status"] == "Return"]))
else:
    c1.metric("Total Active Load", 0)
    c2.metric("Pending Dispatch", 0)
    c3.metric("Successfully Cleared", 0)
    c4.metric("Flagged Returns", 0)

st.markdown("###")

# ====================================================================
# NEW: LOGISTICS ARCHIVE MANAGEMENT ENGINE (TAB 1 CLEARANCE)
# ====================================================================
with st.expander("💼 LOGISTICS ARCHIVE MANAGEMENT SYSTEM", expanded=False):
    st.markdown("""
        <small style='color: #94A3B8;'>
        Safely offload historical, finalized dispatches directly to the 'Archived_Dispatches' cold-storage sheet 
        to ensure instantaneous speeds for your background loops.
        </small>
    """, unsafe_allow_html=True)
    
    col_arch1, col_arch2, col_arch3 = st.columns([2, 2, 3])
    
    with col_arch1:
        min_date = df_dispatch["Date_Issued"].min() if not df_dispatch.empty and pd.notna(df_dispatch["Date_Issued"].min()) else datetime.today()
        start_archive_date = st.date_input("Start Threshold Date", value=min_date)
    with col_arch2:
        end_archive_date = st.date_input("End Threshold Date", value=datetime.today())
        
    t_start = pd.to_datetime(start_archive_date)
    t_end = pd.to_datetime(end_archive_date)
    
    # Isolate archival items: matching standard date scope AND closed statuses only!
    if not df_dispatch.empty:
        archive_eligible = df_dispatch[
            (df_dispatch["Date_Issued"] >= t_start) & 
            (df_dispatch["Date_Issued"] <= t_end) & 
            (df_dispatch["Status"].isin(["Dispatched", "Return"]))
        ]
    else:
        archive_eligible = pd.DataFrame()
    
    with col_arch3:
        st.markdown("##### Archive Migration Summary")
        st.write(f"📦 Records Identified for Archiving: **{len(archive_eligible)} rows**")
        if not archive_eligible.empty:
            st.caption("⚠️ Operational Safety Lock: 'Pending' status items will be skipped to protect active dispatches.")

    if not archive_eligible.empty:
        if st.button("⚡ EXECUTE SECURE BULK ARCHIVE", use_container_width=True):
            with st.status("Migrating records across distributed cloud systems...", expanded=True) as status_indicator:
                gc = get_google_client()
                if gc:
                    try:
                        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
                        # Targets the second tab inside your Google Sheet (Index 1)
                        archive_worksheet = sh.get_worksheet(1) 
                        
                        status_indicator.write("Parsing archive package schema...")
                        df_to_archive = archive_eligible.copy()
                        df_to_archive["Date_Issued"] = df_to_archive["Date_Issued"].apply(
                            lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) and hasattr(x, 'strftime') else str(x)
                        )
                        archive_rows = df_to_archive.fillna("").astype(str).values.tolist()
                        
                        status_indicator.write("Streaming payload entries to 'Archived_Dispatches'...")
                        archive_worksheet.append_rows(archive_rows)
                        
                        status_indicator.write("Purging archived entries from operational data layout...")
                        remaining_dispatch_df = df_dispatch.drop(archive_eligible.index)
                        
                        status_indicator.write("Synchronizing lean registry states back to main sheet...")
                        success = save_sheet_data(remaining_dispatch_df, 0, "Date_Issued")
                        
                        if success:
                            st.session_state.dispatch_data = remaining_dispatch_df
                            status_indicator.update(label="Archive Migration Complete! Live systems optimized.", state="complete")
                            st.success(f"Success! Safely relocated {len(archive_eligible)} rows to cold storage.")
                            st.rerun()
                        else:
                            status_indicator.update(label="Migration failed during target synchronization.", state="error")
                    except Exception as archive_err:
                        status_indicator.update(label=f"Archive Error: {archive_err}", state="error")
                        st.error(f"Sync Fault encountered: {archive_err}")
    else:
        st.button("⚡ NO ARCHIVABLE RECORDS FOUND WITHIN DATE BOUNDS", disabled=True, use_container_width=True)

st.markdown("---")

# ====================================================================
# LIVE WORKSPACE GRID (DATA EDITOR)
# ====================================================================
if filt.empty:
    st.warning("⚠️ System Online: No matching rows found or waiting for Cloud interface link connection.")
else:
    edited_dispatch = st.data_editor(
        filt,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=["Pending","Dispatched","Return"], required=True),
            "Remarks": st.column_config.TextColumn("Warehouse Remarks Field", width="large")
        },
        disabled=["DO_Number", "Last_4", "Date_Issued", "Warehouse_Name", "Created_By", "Last_Modified"]
    )
    
    if st.button("💾 SAVE DISPATCH MODIFICATIONS", use_container_width=True):
        for _, row in edited_dispatch.iterrows():
            do_val = str(row["DO_Number"]).strip()
            df_dispatch.loc[df_dispatch["DO_Number"] == do_val, "Status"] = row["Status"]
            df_dispatch.loc[df_dispatch["DO_Number"] == do_val, "Remarks"] = row["Remarks"]
            df_dispatch.loc[df_dispatch["DO_Number"] == do_val, "Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        if save_sheet_data(df_dispatch, 0, "Date_Issued"):
            st.session_state.dispatch_data = df_dispatch
            st.success("Logistics database updated and synced successfully!")
            st.rerun()
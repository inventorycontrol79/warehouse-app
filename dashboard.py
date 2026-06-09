import streamlit as st
import pandas as pd
import altair as alt
import io
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
st.set_page_config(page_title="SABIN PLASTIC // Command Center", layout="wide")

INVENTORY_FILE = "inventory.csv"
BOT_STATUS_FILE = "bot_status.txt"

# Auto-refresh system every 30 seconds to fetch live data
st_autorefresh(interval=30000, key="auto_refresh")

# --- PREMIUM CORPORATE ERP STYLING & CONTRAST FIXES ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    /* Global App Canvas */
    .stApp {
        background-color: #0B0F19; /* Deep Corporate Slate */
        color: #E2E8F0;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Critical Visibility Fix for Default Streamlit Elements */
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p {
        color: #F8FAFC !important; /* Luminous Off-White */
    }
    
    /* Form Titles & Labels Contrast */
    label, .stWidgetLabel p {
        color: #94A3B8 !important;
        font-weight: 600 !important;
    }
    
    /* Sleek Enterprise Header Structure */
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
        color: #0EA5E9 !important; /* Corporate Blue Accent */
    }
    .sabin-sub {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 3px;
        color: #94A3B8 !important; /* Clearly Visible Silver/Slate */
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* Structured Corporate Metrics */
    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1E293B;
        border-top: 3px solid #0EA5E9; /* Corporate Blue Accent Border */
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
    
    /* Clean Sidebar Separation and Contrast */
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
        <div class='sabin-sub'>Enterprise Logistics Operations Terminal</div>
    </div>
""", unsafe_allow_html=True)

# --- ENGINE DATA LOADING ---
def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        return pd.read_csv(INVENTORY_FILE)
    return pd.DataFrame(columns=[
        "DO_Number","Last_4","Status","Date_Issued",
        "Warehouse_Name","Remarks","Created_By","Last_Modified"
    ])

df = load_inventory()

# --- SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### ⚙️ SYSTEM CONTROLS")

uploaded = st.sidebar.file_uploader("Upload ERP Excel", type=["xlsx"])

if uploaded is not None:
    erp = pd.read_excel(uploaded, engine="openpyxl")
    
    new_df = pd.DataFrame({
        "DO_Number": erp["Voucher No"].astype(str).str.replace("DLNS:","", regex=False),
        "Date_Issued": erp["Date"],
        "Warehouse_Name": erp["Godown"].astype(str).str.strip().str.title(),
        "Created_By": erp["Created By"]
    })

    new_df["Last_4"] = new_df["DO_Number"].str[-4:]
    new_df["Status"] = "Pending"
    new_df["Remarks"] = ""
    new_df["Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    combined = pd.concat([df,new_df], ignore_index=True)
    combined.drop_duplicates(subset=["DO_Number"], keep="last", inplace=True)
    combined.to_csv(INVENTORY_FILE, index=False)

    df = combined
    st.sidebar.success("Database synchronized successfully.")

if not df.empty:
    df["Date_Issued"] = pd.to_datetime(df["Date_Issued"], errors="coerce")
    df["Warehouse_Name"] = df["Warehouse_Name"].astype(str).str.strip().str.title()

search = st.sidebar.text_input("🔍 Global DO Search")

warehouse_options = ["All"]
if not df.empty:
    warehouse_options += sorted(df["Warehouse_Name"].astype(str).unique().tolist())

warehouse = st.sidebar.selectbox("Filter Facility", warehouse_options)
status = st.sidebar.selectbox("Filter Status", ["All","Pending","Dispatched","Return"])

if not df.empty:
    min_date = df["Date_Issued"].min().date()
    max_date = df["Date_Issued"].max().date()
else:
    today = datetime.today().date()
    min_date = today
    max_date = today

st.sidebar.markdown("### 📅 TIMEFRAME")
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)

# Automation System Status Check
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

if search:
    mask = filt.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
    filt = filt[mask]
if warehouse != "All": filt = filt[filt["Warehouse_Name"] == warehouse]
if status != "All": filt = filt[filt["Status"] == status]

if not filt.empty:
    filt = filt[(filt["Date_Issued"].dt.date >= start_date) & (filt["Date_Issued"].dt.date <= end_date)]

# --- EXECUTIVE METRIC CARDS ---
total = len(filt)
dispatched = len(filt[filt["Status"]=="Dispatched"])
pending = len(filt[filt["Status"]=="Pending"])
returned = len(filt[filt["Status"]=="Return"])

dispatch_rate = round((dispatched/total)*100,1) if total else 0

# Evaluates ageing metrics STRICTLY for Pending orders (Excluding Returns and Dispatched items)
pending_only = filt[filt["Status"] == "Pending"]
avg_age = round(((pd.Timestamp.today() - pending_only["Date_Issued"]).dt.days).mean(), 1) if not pending_only.empty else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("TOTAL DO", total)
c2.metric("DISPATCHED", dispatched)
c3.metric("PENDING", pending)
c4.metric("RETURNS", returned)
c5.metric("DISPATCH %", f"{dispatch_rate}%")
c6.metric("AVG PENDING AGE", f"{avg_age} Days")

st.markdown("###")

# --- EXECUTIVE DATA DATA VISUALIZATIONS ---
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
    if not filt.empty:
        warehouse_summary = filt.groupby("Warehouse_Name").agg(Total=("DO_Number","count")).reset_index().sort_values("Total", ascending=False)
        st.dataframe(warehouse_summary, use_container_width=True, hide_index=True)

# Ageing Analysis Queue Execution
if not pending_only.empty:
    st.markdown("---")
    st.markdown("##### Critical Ageing Queue (Pending Orders Only)")
    pending_only["Age_Days"] = (pd.Timestamp.today() - pending_only["Date_Issued"]).dt.days
    def risk(x):
        if x >= 6: return "🔴 High Risk"
        elif x >= 3: return "🟡 Attention"
        return "🟢 Standard"
    pending_only["Risk_Profile"] = pending_only["Age_Days"].apply(risk)
    st.dataframe(pending_only[["DO_Number","Warehouse_Name","Age_Days","Risk_Profile"]].sort_values("Age_Days", ascending=False), use_container_width=True, hide_index=True)

# --- LIVE OPERATIONS INTERACTIVE LEDGER ---
st.markdown("---")
st.markdown("##### Active Operations Ledger")
edited = st.data_editor(
    filt,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.SelectboxColumn("Status", options=["Pending","Dispatched","Return"])
    },
    disabled=["DO_Number", "Last_4", "Date_Issued", "Warehouse_Name", "Created_By"]
)

if st.button("💾 COMMIT RECORD TO DATABASE"):
    base = load_inventory()
    for _, row in edited.iterrows():
        do = row["DO_Number"]
        base.loc[base["DO_Number"]==do, "Status"] = row["Status"]
        base.loc[base["DO_Number"]==do, "Remarks"] = row["Remarks"]
        base.loc[base["DO_Number"]==do, "Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    base.to_csv(INVENTORY_FILE, index=False)
    st.success("System updated successfully.")

# --- EXECUTIVE EXCEL SECURED REPORT ENGINE ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    summary = pd.DataFrame({"Metric":["Total DO","Dispatched","Pending","Return","Dispatch %"], "Value":[total,dispatched,pending,returned,f"{dispatch_rate}%"]})
    summary.to_excel(writer, sheet_name="Executive Summary", index=False)
    filt.to_excel(writer, sheet_name="Dispatch Records", index=False)
    
    wb = writer.book
    header = wb.add_format({"bold":True, "bg_color":"#0F172A", "font_color":"white"})
    
    for sheet in ["Executive Summary","Dispatch Records"]:
        ws = writer.sheets[sheet]
        ws.freeze_panes(1,0)
        cols = summary.columns if sheet == "Executive Summary" else filt.columns
        for col_num, value in enumerate(cols):
            ws.write(0, col_num, value, header)
            ws.set_column(col_num, col_num, 20)

st.markdown("###")
st.download_button("📥 DOWNLOAD SECURE LEDGER (XLSX)", buffer.getvalue(), "SABIN_Enterprise_Logistics.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
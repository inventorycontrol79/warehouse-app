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

# Auto-refresh every 30 seconds
st_autorefresh(interval=30000, key="auto_refresh")

# --- PREMIUM CSS STYLING ---
st.markdown("""
    <style>
    .stApp {
        background:
        linear-gradient(rgba(9,12,18,.95),rgba(9,12,18,.95)),
        repeating-linear-gradient(90deg,transparent 0px,transparent 79px,rgba(251,191,36,.035) 80px),
        repeating-linear-gradient(0deg,transparent 0px,transparent 79px,rgba(251,191,36,.035) 80px),
        radial-gradient(circle at 20% 30%,rgba(56,189,248,.05),transparent 30%),
        radial-gradient(circle at 80% 70%,rgba(16,185,129,.04),transparent 30%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,.03);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 18px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg,#0f172a,#111827);
    }
    .sabin-title {
        font-family: 'Montserrat', sans-serif; 
        font-size: 50px; 
        font-weight: 900; 
        letter-spacing: 15px; 
        color: #ffffff; 
        text-transform: uppercase;
        margin-bottom: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
    <div style='padding:30px; border-radius:20px; background:rgba(255,255,255,.03); border:1px solid rgba(255,255,255,.05); margin-bottom:30px;'>
        <div class='sabin-title'>SABIN PLASTIC</div>
        <div style='color:#fbbf24; letter-spacing: 6px; font-size: 14px; text-transform: uppercase;'>Warehouse Delivery Command Center</div>
    </div>
""", unsafe_allow_html=True)

# --- DATA HANDLING ---
def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        return pd.read_csv(INVENTORY_FILE)
    return pd.DataFrame(columns=[
        "DO_Number","Last_4","Status","Date_Issued",
        "Warehouse_Name","Remarks","Created_By","Last_Modified"
    ])

df = load_inventory()

# --- SIDEBAR: COMMAND CENTER ---
st.sidebar.header("⚙️ COMMAND CENTER")

uploaded = st.sidebar.file_uploader("Upload ERP Excel", type=["xlsx"])

if uploaded is not None:
    erp = pd.read_excel(uploaded, engine="openpyxl")
    
    new_df = pd.DataFrame({
        "DO_Number": erp["Voucher No"].astype(str).str.replace("DLNS:","", regex=False),
        "Date_Issued": erp["Date"],
        "Warehouse_Name": erp["Godown"].astype(str).str.strip().str.title(), # Auto-Polish
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
    st.sidebar.success("Inventory updated successfully")

if not df.empty:
    df["Date_Issued"] = pd.to_datetime(df["Date_Issued"], errors="coerce")
    df["Warehouse_Name"] = df["Warehouse_Name"].astype(str).str.strip().str.title() # Auto-Polish existing data

search = st.sidebar.text_input("🔍 Global Search")

warehouse_options = ["All"]
if not df.empty:
    warehouse_options += sorted(df["Warehouse_Name"].astype(str).unique().tolist())

warehouse = st.sidebar.selectbox("Filter Warehouse", warehouse_options)
status = st.sidebar.selectbox("Filter Status", ["All","Pending","Dispatched","Return"])

if not df.empty:
    min_date = df["Date_Issued"].min().date()
    max_date = df["Date_Issued"].max().date()
else:
    today = datetime.today().date()
    min_date = today
    max_date = today

st.sidebar.markdown("### 📅 DATE FILTER")
start_date = st.sidebar.date_input("Start Date", min_date)
end_date = st.sidebar.date_input("End Date", max_date)

# Automation Status
st.sidebar.markdown("---")
if os.path.exists(BOT_STATUS_FILE):
    try:
        ts = open(BOT_STATUS_FILE).read().strip()
        last = datetime.strptime(ts,"%Y-%m-%d %H:%M:%S")
        diff = (datetime.now()-last).total_seconds()
        if diff < 120:
            st.sidebar.success("🟢 WhatsApp Bot: Online")
        else:
            st.sidebar.error("🔴 WhatsApp Bot: Offline")
    except:
        st.sidebar.warning("Bot status unavailable")
else:
    st.sidebar.info("🤖 Automation Monitoring Standby")

# --- FILTER LOGIC ---
filt = df.copy()

if search:
    mask = filt.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
    filt = filt[mask]
if warehouse != "All": filt = filt[filt["Warehouse_Name"] == warehouse]
if status != "All": filt = filt[filt["Status"] == status]

if not filt.empty:
    filt = filt[(filt["Date_Issued"].dt.date >= start_date) & (filt["Date_Issued"].dt.date <= end_date)]

# --- EXECUTIVE SUMMARY METRICS ---
total = len(filt)
dispatched = len(filt[filt["Status"]=="Dispatched"])
pending = len(filt[filt["Status"]=="Pending"])
returned = len(filt[filt["Status"]=="Return"])

dispatch_rate = round((dispatched/total)*100,1) if total else 0
avg_age = round(((pd.Timestamp.today()-filt["Date_Issued"]).dt.days).mean(),1) if not filt.empty else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("TOTAL DO", total)
c2.metric("DISPATCHED", dispatched)
c3.metric("PENDING", pending)
c4.metric("RETURNS", returned)
c5.metric("DISPATCH %", f"{dispatch_rate}%")
c6.metric("AVG AGE", f"{avg_age} Days")

# --- CHARTS & ANALYSIS ---
left, right = st.columns([1,1])

with left:
    st.subheader("Pipeline Distribution")
    chart_df = pd.DataFrame({"Status":["Pending","Dispatched","Return"], "Count":[pending,dispatched,returned]})
    chart = alt.Chart(chart_df).mark_arc(innerRadius=85).encode(
        theta="Count:Q",
        color=alt.Color("Status:N", scale=alt.Scale(domain=["Pending","Dispatched","Return"], range=["#fbbf24","#10b981","#ef4444"])),
        tooltip=["Status","Count"]
    ).properties(height=350, background="transparent").configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

with right:
    st.subheader("Warehouse Leaderboard")
    if not filt.empty:
        warehouse_summary = filt.groupby("Warehouse_Name").agg(Total=("DO_Number","count")).reset_index().sort_values("Total", ascending=False)
        st.dataframe(warehouse_summary, use_container_width=True, hide_index=True)

# Ageing Analysis
if not filt.empty:
    pending_df = filt[filt["Status"]=="Pending"].copy()
    if not pending_df.empty:
        pending_df["Age_Days"] = (pd.Timestamp.today()-pending_df["Date_Issued"]).dt.days
        def risk(x):
            if x >= 6: return "🔴 Critical"
            elif x >= 3: return "🟡 Attention"
            return "🟢 Normal"
        pending_df["Risk"] = pending_df["Age_Days"].apply(risk)
        st.subheader("Pending Ageing Analysis")
        st.dataframe(pending_df[["DO_Number","Warehouse_Name","Age_Days","Risk"]], use_container_width=True, hide_index=True)

# --- LIVE OPERATIONS GRID ---
st.subheader("Operations Grid")
edited = st.data_editor(
    filt,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.SelectboxColumn("Status", options=["Pending","Dispatched","Return"])
    },
    disabled=["DO_Number", "Last_4", "Date_Issued", "Warehouse_Name", "Created_By"]
)

if st.button("💾 COMMIT OPERATIONS CHANGES"):
    base = load_inventory()
    for _, row in edited.iterrows():
        do = row["DO_Number"]
        base.loc[base["DO_Number"]==do, "Status"] = row["Status"]
        base.loc[base["DO_Number"]==do, "Remarks"] = row["Remarks"]
        base.loc[base["DO_Number"]==do, "Last_Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    base.to_csv(INVENTORY_FILE, index=False)
    st.success("Logistics grid successfully updated.")

# --- EXECUTIVE EXCEL EXPORT ---
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    summary = pd.DataFrame({"Metric":["Total DO","Dispatched","Pending","Return","Dispatch %"], "Value":[total,dispatched,pending,returned,f"{dispatch_rate}%"]})
    summary.to_excel(writer, sheet_name="Executive Summary", index=False)
    filt.to_excel(writer, sheet_name="Dispatch Records", index=False)
    
    wb = writer.book
    header = wb.add_format({"bold":True, "bg_color":"#1E293B", "font_color":"white"})
    
    for sheet in ["Executive Summary","Dispatch Records"]:
        ws = writer.sheets[sheet]
        ws.freeze_panes(1,0)
        cols = summary.columns if sheet == "Executive Summary" else filt.columns
        for col_num, value in enumerate(cols):
            ws.write(0, col_num, value, header)
            ws.set_column(col_num, col_num, 20)

st.download_button("📥 DOWNLOAD EXECUTIVE REPORT", buffer.getvalue(), "SABIN_Logistics.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
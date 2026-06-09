import streamlit as st
import pandas as pd
import altair as alt
import io
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="SABIN PLASTIC Command Center", layout="wide")

st_autorefresh(interval=30000, key="refresh")

st.markdown("""
<style>
.stApp{
background:
linear-gradient(rgba(8,11,17,.96),rgba(8,11,17,.96)),
repeating-linear-gradient(90deg,transparent 0px,transparent 39px,rgba(255,255,255,.03) 40px),
repeating-linear-gradient(0deg,transparent 0px,transparent 39px,rgba(255,255,255,.03) 40px);
color:white;
}
.block-container{padding-top:1rem;}
.kpi{
background:rgba(255,255,255,.05);
padding:15px;border-radius:15px;
border:1px solid rgba(255,255,255,.08);
}
</style>
""", unsafe_allow_html=True)

INVENTORY_FILE = "inventory.csv"

st.title("SABIN PLASTIC")
st.caption("Warehouse Delivery Command Center")

def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        return pd.read_csv(INVENTORY_FILE)
    return pd.DataFrame(columns=[
        "DO_Number","Last_4","Status","Date_Issued",
        "Warehouse_Name","Remarks","Created_By"
    ])

df = load_inventory()

st.sidebar.header("Command Center")

uploaded = st.sidebar.file_uploader(
    "Upload ERP Excel",
    type=["xlsx"]
)

if uploaded:
    erp = pd.read_excel(uploaded)

    new_df = pd.DataFrame()
    new_df["DO_Number"] = erp["Voucher No"].astype(str).str.replace("DLNS:","", regex=False)
    new_df["Last_4"] = new_df["DO_Number"].str[-4:]
    new_df["Status"] = "Pending"
    new_df["Date_Issued"] = erp["Date"]
    new_df["Warehouse_Name"] = erp["Godown"]
    new_df["Remarks"] = ""
    new_df["Created_By"] = erp["Created By"]

    combined = pd.concat([df,new_df], ignore_index=True)
    combined.drop_duplicates(subset=["DO_Number"], keep="last", inplace=True)

    combined.to_csv(INVENTORY_FILE,index=False)
    df = combined

    st.sidebar.success("Inventory updated successfully")

if not df.empty:
    df["Date_Issued"] = pd.to_datetime(df["Date_Issued"], errors="coerce")

search = st.sidebar.text_input("Search")
warehouse = st.sidebar.selectbox(
    "Warehouse",
    ["All"] + sorted(df["Warehouse_Name"].astype(str).unique().tolist()) if not df.empty else ["All"]
)
status = st.sidebar.selectbox(
    "Status",
    ["All","Pending","Dispatched","Return"]
)

filt = df.copy()

if search:
    mask = filt.astype(str).apply(
        lambda c: c.str.contains(search, case=False, na=False)
    ).any(axis=1)
    filt = filt[mask]

if warehouse != "All":
    filt = filt[filt["Warehouse_Name"] == warehouse]

if status != "All":
    filt = filt[filt["Status"] == status]

total = len(filt)
dispatched = len(filt[filt["Status"]=="Dispatched"])
pending = len(filt[filt["Status"]=="Pending"])
returned = len(filt[filt["Status"]=="Return"])

rate = round((dispatched/total)*100,1) if total else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("TOTAL DO", total)
c2.metric("DISPATCHED", dispatched)
c3.metric("PENDING", pending)
c4.metric("RETURN", returned)
c5.metric("DISPATCH %", f"{rate}%")

left,right = st.columns([1,1])

with left:
    status_df = pd.DataFrame({
        "Status":["Pending","Dispatched","Return"],
        "Count":[pending,dispatched,returned]
    })

    chart = alt.Chart(status_df).mark_arc(innerRadius=70).encode(
        theta="Count",
        color="Status",
        tooltip=["Status","Count"]
    )
    st.altair_chart(chart, use_container_width=True)

with right:
    if not filt.empty:
        summary = filt.groupby("Warehouse_Name").agg(
            Total=("DO_Number","count")
        ).reset_index().sort_values("Total", ascending=False)
        st.subheader("Warehouse Leaderboard")
        st.dataframe(summary, use_container_width=True)

if not filt.empty:
    pending_df = filt[filt["Status"]=="Pending"].copy()

    if not pending_df.empty:
        pending_df["Age_Days"] = (
            pd.Timestamp.today() - pd.to_datetime(pending_df["Date_Issued"])
        ).dt.days

        def risk(x):
            if x >= 6:
                return "Critical"
            elif x >= 3:
                return "Attention"
            return "Normal"

        pending_df["Risk"] = pending_df["Age_Days"].apply(risk)

        st.subheader("Pending Ageing Analysis")
        st.dataframe(
            pending_df[["DO_Number","Warehouse_Name","Age_Days","Risk"]],
            use_container_width=True
        )

st.subheader("Operations Grid")

edited = st.data_editor(
    filt,
    use_container_width=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=["Pending","Dispatched","Return"]
        ),
        "Remarks": st.column_config.TextColumn("Remarks")
    },
    disabled=[
        "DO_Number","Last_4","Date_Issued",
        "Warehouse_Name","Created_By"
    ]
)

if st.button("SAVE CHANGES"):
    base = load_inventory()

    for _, row in edited.iterrows():
        do = row["DO_Number"]
        base.loc[base["DO_Number"]==do, "Status"] = row["Status"]
        base.loc[base["DO_Number"]==do, "Remarks"] = row["Remarks"]

    base.to_csv(INVENTORY_FILE,index=False)
    st.success("Changes saved to inventory.csv")

buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    filt.to_excel(writer, sheet_name="Dispatch Records", index=False)

    workbook = writer.book
    ws = writer.sheets["Dispatch Records"]

    header = workbook.add_format({
        "bold": True,
        "bg_color": "#D4AF37",
        "font_color": "black"
    })

    for col_num, value in enumerate(filt.columns.values):
        ws.write(0, col_num, value, header)

    ws.freeze_panes(1,0)

    for i, col in enumerate(filt.columns):
        width = max(len(col), 15)
        ws.set_column(i,i,width)

st.download_button(
    "Download Executive Report",
    buffer.getvalue(),
    "SABIN_Logistics.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
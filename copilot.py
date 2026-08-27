import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# =====================================================
# FAST CLOUD CACHE & INGESTION ENGINE
# =====================================================
def get_or_fetch_stock_data(force_reload=False):
    """Retrieves live stock data with session cache to eliminate round-trip latency."""
    if not force_reload and "df_stock_live" in st.session_state and st.session_state.df_stock_live is not None and not st.session_state.df_stock_live.empty:
        return st.session_state.df_stock_live

    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        
        ws = sh.get_worksheet(3)
        raw_data = ws.get_all_values()
        if raw_data:
            headers = [str(h).strip() for h in raw_data[0]]
            df = pd.DataFrame(raw_data[1:], columns=headers)
            if "" in df.columns:
                df = df.drop(columns=[""])
            st.session_state.df_stock_live = df
            return df
    except Exception:
        pass
    return pd.DataFrame()


def get_or_fetch_do_ledger(force_reload=False):
    """Retrieves DO records with session-level caching."""
    if not force_reload and "master_data" in st.session_state and not st.session_state.master_data.empty:
        return st.session_state.master_data
    try:
        raw_json = st.secrets["GCP_JSON"]
        creds_dict = json.loads(raw_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        
        ws = sh.get_worksheet(0)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        st.session_state.master_data = df
        return df
    except Exception:
        return pd.DataFrame()

# =====================================================
# AGENT TOOLS (HIGH SPEED & TARGETED)
# =====================================================
def query_sku_intelligence(search_query: str) -> str:
    """Looks up inventory balance and runway for specific item codes or product names."""
    df = get_or_fetch_stock_data()
    if df.empty:
        return "Error: Stock dataframe is currently unreachable."

    q = str(search_query).strip().upper()
    match = df[
        (df["Item_Code"].astype(str).str.upper() == q) |
        (df["Item_Name"].astype(str).str.upper().str.contains(q, na=False))
    ]

    if match.empty:
        return f"No inventory record found matching '{search_query}'."

    results = []
    for _, row in match.head(5).iterrows():
        total_stock = float(pd.to_numeric(row.get("Current_Stock", 0), errors='coerce') or 0.0)
        daily_vel = float(pd.to_numeric(row.get("Baseline_Velocity", 0), errors='coerce') or 0.0)
        runway = round(total_stock / daily_vel, 1) if daily_vel > 0 else "Infinite (>90d)"

        results.append({
            "SKU": row.get("Item_Code"),
            "Description": row.get("Item_Name"),
            "Category": row.get("Product_Category"),
            "Total_Balance": total_stock,
            "Daily_Velocity": daily_vel,
            "Days_Runway": runway,
            "Sharjah": {"Stock": float(pd.to_numeric(row.get("Stock_Sharjah", 0), errors='coerce') or 0), "Velocity": float(pd.to_numeric(row.get("Velocity_Sharjah", 0), errors='coerce') or 0)},
            "Al_Quoz": {"Stock": float(pd.to_numeric(row.get("Stock_Al_Quoz", 0), errors='coerce') or 0), "Velocity": float(pd.to_numeric(row.get("Velocity_Al_Quoz", 0), errors='coerce') or 0)},
            "DIP": {"Stock": float(pd.to_numeric(row.get("Stock_DIP", 0), errors='coerce') or 0), "Velocity": float(pd.to_numeric(row.get("Velocity_DIP", 0), errors='coerce') or 0)},
            "Abu_Dhabi": {"Stock": float(pd.to_numeric(row.get("Stock_Abu_Dhabi", 0), errors='coerce') or 0), "Velocity": float(pd.to_numeric(row.get("Velocity_Abu_Dhabi", 0), errors='coerce') or 0)}
        })
    return json.dumps(results, default=str)


def query_transfer_recommendations(destination_branch: str = "All") -> str:
    """Calculates optimal inter-branch stock transfers based on low runway in destination branches."""
    df = get_or_fetch_stock_data()
    if df.empty:
        return "Error: Stock dataframe is unreachable."

    branch_map = {
        "Sharjah": ("Stock_Sharjah", "Velocity_Sharjah"),
        "Al Quoz": ("Stock_Al_Quoz", "Velocity_Al_Quoz"),
        "DIP": ("Stock_DIP", "Velocity_DIP"),
        "Abu Dhabi": ("Stock_Abu_Dhabi", "Velocity_Abu_Dhabi")
    }

    transfers = []
    dest_filter = destination_branch.strip().lower()

    for _, row in df.iterrows():
        sku = str(row.get("Item_Code", "")).strip()
        name = str(row.get("Item_Name", "")).strip()
        
        for dest_name, (d_stock_col, d_vel_col) in branch_map.items():
            if dest_filter != "all" and dest_filter not in dest_name.lower():
                continue

            d_stock = float(pd.to_numeric(row.get(d_stock_col, 0), errors='coerce') or 0)
            d_vel = float(pd.to_numeric(row.get(d_vel_col, 0), errors='coerce') or 0)
            d_runway = (d_stock / d_vel) if d_vel > 0 else 999.0

            if d_vel > 0.05 and d_runway <= 7.0:
                # Find best donor branch
                for donor_name, (s_stock_col, s_vel_col) in branch_map.items():
                    if donor_name == dest_name:
                        continue
                    s_stock = float(pd.to_numeric(row.get(s_stock_col, 0), errors='coerce') or 0)
                    s_vel = float(pd.to_numeric(row.get(s_vel_col, 0), errors='coerce') or 0)
                    s_safe_donor = int(s_stock - (14.0 * s_vel)) if s_vel > 0 else int(s_stock)

                    if s_safe_donor >= 5:
                        transfer_qty = min(int((7.0 * d_vel) - d_stock + 5), s_safe_donor)
                        if transfer_qty > 0:
                            transfers.append({
                                "SKU": sku,
                                "Item_Name": name,
                                "Destination": dest_name,
                                "Deficit_Stock": d_stock,
                                "Deficit_Runway_Days": round(d_runway, 1),
                                "Donor": donor_name,
                                "Donor_Stock": s_stock,
                                "Suggested_Qty": transfer_qty,
                                "ERP_Command": f"SRTS: Move {transfer_qty} units of SKU {sku} from {donor_name} to {dest_name}"
                            })
                            break

    return json.dumps({"Target_Branch": destination_branch, "Total_Transfer_Routes": len(transfers), "Routes": transfers[:10]}, default=str)


def query_reorder_recommendations(days_threshold: int = 7) -> str:
    """Identifies items requiring purchase reorders based on network run-rate."""
    df = get_or_fetch_stock_data()
    if df.empty:
        return "Error: Stock dataframe is unreachable."

    urgent_items = []
    for _, row in df.iterrows():
        total_stock = float(pd.to_numeric(row.get("Current_Stock", 0), errors='coerce') or 0.0)
        daily_vel = float(pd.to_numeric(row.get("Baseline_Velocity", 0), errors='coerce') or 0.0)
        
        if daily_vel > 0.05:
            runway = total_stock / daily_vel
            if runway <= float(days_threshold):
                urgent_items.append({
                    "SKU": row.get("Item_Code"),
                    "Name": row.get("Item_Name"),
                    "Current_Stock": total_stock,
                    "Velocity_Per_Day": round(daily_vel, 2),
                    "Days_Left": round(runway, 1),
                    "Category": row.get("Product_Category")
                })

    urgent_items.sort(key=lambda x: x["Days_Left"])
    return json.dumps({"Threshold_Days": days_threshold, "Total_Urgent_SKUs": len(urgent_items), "Critical_Items": urgent_items[:15]}, default=str)


def query_delivery_orders(do_or_status_query: str) -> str:
    """Looks up DO numbers, customer statuses, and warehouse backlogs."""
    df = get_or_fetch_do_ledger()
    if df.empty:
        return "Error: Delivery Orders ledger is unreachable."

    q = str(do_or_status_query).strip().upper()
    if q in ["PENDING", "DISPATCHED", "RETURN"]:
        sub_df = df[df["Status"].astype(str).str.upper() == q]
        return json.dumps({"Query_Status": q, "Count": len(sub_df), "Sample_DOs": sub_df["DO_Number"].head(10).tolist()})

    match = df[df["DO_Number"].astype(str).str.contains(q, case=False, na=False)]
    if match.empty:
        return f"No DO record found matching '{do_or_status_query}'."

    return json.dumps(match.head(5)[["DO_Number", "Status", "Date_Issued", "Warehouse_Name", "Remarks"]].to_dict(orient="records"), default=str)


def get_global_kpis() -> str:
    """Returns global operational KPIs across inventory and dispatch queues."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()

    return json.dumps({
        "Total_SKUs": len(df_s) if not df_s.empty else 0,
        "Total_Stock_Units": int(pd.to_numeric(df_s["Current_Stock"], errors='coerce').sum()) if not df_s.empty else 0,
        "Pending_DO_Count": len(df_do[df_do["Status"].astype(str).str.upper() == "PENDING"]) if not df_do.empty else 0,
        "Dispatched_DO_Count": len(df_do[df_do["Status"].astype(str).str.upper() == "DISPATCHED"]) if not df_do.empty else 0
    })

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer & Senior Demand Planner for Sabin Plastic.
You operate natively inside the enterprise warehouse dashboard with direct access to live inventory and dispatch ledgers.

Core Directives:
1. Inter-Branch Transfers:
   - When asked about transfers to a branch (e.g. Abu Dhabi, Sharjah), always call `query_transfer_recommendations`.
   - Provide direct transfer recommendations along with the Focus ERP command:
     `SRTS: Move [Qty] units of SKU [SKU] from [Donor] to [Destination]`
2. Reorders & Procurement:
   - When asked which items to reorder, use `query_reorder_recommendations`.
3. Tone:
   - Concise, direct, and structured with bold highlights and bullet points.
"""

# =====================================================
# UI INJECTION & MODAL LOGIC
# =====================================================
@st.dialog("🤖 Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    st.markdown("""
        <style>
        div[data-testid="stDialog"] div[role="dialog"] {
            background-color: #0B0F19 !important;
            border: 1px solid #1E293B !important;
            border-radius: 12px !important;
        }
        div[data-testid="stDialog"] h2, 
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"],
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"] * {
            color: #38BDF8 !important;
            font-weight: 800 !important;
            font-size: 22px !important;
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
            border: 1px solid #334155 !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button:hover {
            background-color: #0EA5E9 !important;
            color: #0B0F19 !important;
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button p {
            color: inherit !important;
        }
        div[data-testid="stChatMessage"] {
            background-color: #111827 !important;
            border: 1px solid #1E293B !important;
            border-radius: 8px !important;
            margin-bottom: 12px !important;
            padding: 12px !important;
        }
        div[data-testid="stChatMessage"] p, 
        div[data-testid="stChatMessage"] li, 
        div[data-testid="stChatMessage"] span {
            color: #F8FAFC !important;
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
        div[data-testid="stChatMessage"] strong {
            color: #38BDF8 !important;
        }
        div[data-testid="stChatMessage"] code {
            color: #38BDF8 !important;
            background-color: #020617 !important;
            border: 1px solid #1E293B !important;
        }
        div[data-testid="stChatInput"] {
            background-color: #020617 !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stChatInput"] textarea {
            color: #F8FAFC !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col_hdr, col_clear = st.columns([3, 1])
    with col_hdr:
        st.caption("⚡ Direct Engine: Active Inventory, Demand Velocities & Dispatch Queues")
    with col_clear:
        if st.button("🗑️ Reset & Sync", use_container_width=True):
            st.session_state.copilot_history = []
            get_or_fetch_stock_data(force_reload=True)
            get_or_fetch_do_ledger(force_reload=True)
            st.rerun()

    st.markdown("<small style='color:#94A3B8;'>Quick Queries:</small>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True):
        quick_query = "Which items do we need to reorder within 1 week based on current burn rate?"
    if c2.button("📦 Pending DO Status", use_container_width=True):
        quick_query = "Summarize our current pending Delivery Orders and backlog."
    if c3.button("🔄 Abu Dhabi Transfers", use_container_width=True):
        quick_query = "Which items do I need to transfer to Abu Dhabi in the next few days?"

    if "copilot_history" not in st.session_state:
        st.session_state.copilot_history = []

    for msg in st.session_state.copilot_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about stock levels, reorders, DO status, or branch transfers...")
    query_to_process = quick_query if quick_query else user_input

    if query_to_process:
        st.session_state.copilot_history.append({"role": "user", "content": query_to_process})
        with st.chat_message("user"):
            st.markdown(query_to_process)

        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            # Direct model assignment to remove round-trip network discovery delays
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools=[query_sku_intelligence, query_transfer_recommendations, query_reorder_recommendations, query_delivery_orders, get_global_kpis]
            )
            chat_session = model.start_chat(enable_automatic_function_calling=True)

            with st.spinner("Analyzing warehouse records..."):
                response = chat_session.send_message(query_to_process)
                answer = response.text

        except Exception as err:
            answer = f"⚠️ **Copilot System Notice:** {err}"

        st.session_state.copilot_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)


def inject_floating_copilot():
    """Renders a floating glassmorphism AI Copilot button pinned to the bottom-right viewport."""
    st.markdown("""
        <style>
        .st-key-floating_copilot_btn {
            position: fixed !important;
            bottom: 25px !important;
            right: 30px !important;
            z-index: 999999 !important;
            width: auto !important;
        }

        .st-key-floating_copilot_btn > button {
            background: linear-gradient(135deg, #0EA5E9 0%, #2563EB 50%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            border-radius: 50px !important;
            padding: 10px 24px !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            box-shadow: 0 8px 30px rgba(14, 165, 233, 0.5) !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
        }

        .st-key-floating_copilot_btn > button:hover {
            transform: scale(1.05) !important;
            box-shadow: 0 12px 38px rgba(14, 165, 233, 0.7) !important;
            border-color: rgba(255, 255, 255, 0.6) !important;
            color: #FFFFFF !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Copilot AI", key="floating_copilot_btn"):
        render_copilot_modal()
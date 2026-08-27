import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# =====================================================
# INDEPENDENT CLOUD FALLBACK & DATA INGESTION ENGINE
# =====================================================
def get_or_fetch_stock_data(force_reload=False):
    """Ensures the Copilot has immediate access to live inventory data across all pages."""
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
    """Accesses active DO master dispatch data from Worksheet 0."""
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
# AGENT TOOLS (TOKEN OPTIMIZED)
# =====================================================
def query_sku_intelligence(search_query: str) -> str:
    """Looks up stock, facility distribution, daily velocities, and runway for specific SKUs."""
    df = get_or_fetch_stock_data()
    if df.empty:
        return "Error: Live stock data is currently unreachable."

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
            "Daily_Run_Rate": daily_vel,
            "Coverage_Days": runway,
            "Class": row.get("ABC_Category"),
            "Warehouses": {
                "Sharjah": {
                    "Stock": float(pd.to_numeric(row.get("Stock_Sharjah", 0), errors='coerce') or 0),
                    "Velocity": float(pd.to_numeric(row.get("Velocity_Sharjah", 0), errors='coerce') or 0)
                },
                "Al_Quoz": {
                    "Stock": float(pd.to_numeric(row.get("Stock_Al_Quoz", 0), errors='coerce') or 0),
                    "Velocity": float(pd.to_numeric(row.get("Velocity_Al_Quoz", 0), errors='coerce') or 0)
                },
                "DIP": {
                    "Stock": float(pd.to_numeric(row.get("Stock_DIP", 0), errors='coerce') or 0),
                    "Velocity": float(pd.to_numeric(row.get("Velocity_DIP", 0), errors='coerce') or 0)
                },
                "Abu_Dhabi": {
                    "Stock": float(pd.to_numeric(row.get("Stock_Abu_Dhabi", 0), errors='coerce') or 0),
                    "Velocity": float(pd.to_numeric(row.get("Velocity_Abu_Dhabi", 0), errors='coerce') or 0)
                }
            }
        })
    return json.dumps(results, default=str)


def query_reorder_recommendations(days_threshold: int = 7) -> str:
    """Finds all SKUs across the network that will run out of stock within the given number of days."""
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
    return json.dumps({
        "Threshold_Days": days_threshold,
        "Total_Urgent_SKUs": len(urgent_items),
        "Critical_Items": urgent_items[:15]
    }, default=str)


def query_delivery_orders(do_or_status_query: str) -> str:
    """Looks up DO numbers, customer statuses, and warehouse backlogs."""
    df = get_or_fetch_do_ledger()
    if df.empty:
        return "Error: Delivery Orders ledger is unreachable."

    q = str(do_or_status_query).strip().upper()
    if q in ["PENDING", "DISPATCHED", "RETURN"]:
        sub_df = df[df["Status"].astype(str).str.upper() == q]
        return json.dumps({
            "Query_Status": q,
            "Count": len(sub_df),
            "Sample_DOs": sub_df["DO_Number"].head(10).tolist()
        })

    match = df[df["DO_Number"].astype(str).str.contains(q, case=False, na=False)]
    if match.empty:
        return f"No DO record found matching '{do_or_status_query}'."

    records = match.head(5)[["DO_Number", "Status", "Date_Issued", "Warehouse_Name", "Remarks"]].to_dict(orient="records")
    return json.dumps(records, default=str)


def get_global_kpis() -> str:
    """Returns global operational KPIs across inventory and dispatch queues."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()

    summary = {
        "Total_SKUs": len(df_s) if not df_s.empty else 0,
        "Total_Stock_Units": int(pd.to_numeric(df_s["Current_Stock"], errors='coerce').sum()) if not df_s.empty else 0,
        "Pending_DO_Count": len(df_do[df_do["Status"].astype(str).str.upper() == "PENDING"]) if not df_do.empty else 0,
        "Dispatched_DO_Count": len(df_do[df_do["Status"].astype(str).str.upper() == "DISPATCHED"]) if not df_do.empty else 0
    }
    return json.dumps(summary)

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer & Senior Demand Planner for Sabin Plastic.
You operate natively inside the enterprise warehouse dashboard with direct access to live inventory and dispatch ledgers.

Core Directives:
1. Demand Runway: Always evaluate stock health using Days of Coverage (Current Stock / Daily Velocity).
2. Inter-Branch Transfers:
   - Deficit: Branch has <= 7 days runway.
   - Donor: Branch must retain >= 14 days runway after transferring.
   - When suggesting a transfer, provide the exact Focus ERP command:
     `SRTS: Move [Qty] units of SKU [SKU] from [Donor] to [Destination]`
3. Reorders & Procurement:
   - When asked which items to reorder, use `query_reorder_recommendations` and list items ordered by lowest runway days first.
   - Mention lead time buffer (14-21 days) when calculating reorder urgency.
4. Tone & Style:
   - Crisp, analytical, executive, and structured with bold highlights and bullet points.
"""

# =====================================================
# UI INJECTION & MODAL LOGIC (FIXED DARK CONTRAST & DYNAMIC ENDPOINT)
# =====================================================
@st.dialog("🤖 Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    # Force dark background, high-contrast title, visible buttons, and clear text
    st.markdown("""
        <style>
        /* 1. Modal Dialog Outer Surface */
        div[data-testid="stDialog"] div[role="dialog"] {
            background-color: #0B0F19 !important;
            border: 1px solid #1E293B !important;
            border-radius: 12px !important;
        }
        div[data-testid="stDialog"] div[data-testid="stVerticalBlock"] {
            background-color: transparent !important;
        }

        /* 2. Modal Header Title & Close Icon */
        div[data-testid="stDialog"] h2, 
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"],
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"] * {
            color: #38BDF8 !important;
            font-weight: 800 !important;
            font-size: 22px !important;
        }
        div[data-testid="stDialog"] button[aria-label="Close"] svg {
            fill: #94A3B8 !important;
        }

        /* 3. Action Buttons & Quick Query Chips */
        div[data-testid="stDialog"] div[data-testid="stButton"] button {
            background-color: #1E293B !important;
            color: #F8FAFC !important;
            border: 1px solid #334155 !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button:hover {
            background-color: #0EA5E9 !important;
            color: #0B0F19 !important;
            border-color: #38BDF8 !important;
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button p {
            color: inherit !important;
        }

        /* 4. Subtitles, Labels & Captions */
        div[data-testid="stDialog"] small,
        div[data-testid="stDialog"] [data-testid="stCaptionContainer"] p {
            color: #94A3B8 !important;
        }

        /* 5. Chat History Message Cards */
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

        /* 6. Chat Input Container */
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

    # Top Control Bar (Clear Cache & Reset)
    col_hdr, col_clear = st.columns([3, 1])
    with col_hdr:
        st.caption("⚡ Live Connected: Live Stock, DO Tracker, and Movement Velocities")
    with col_clear:
        if st.button("🗑️ Reset & Sync", use_container_width=True, help="Clear chat history and re-fetch latest Google Sheets data"):
            st.session_state.copilot_history = []
            get_or_fetch_stock_data(force_reload=True)
            get_or_fetch_do_ledger(force_reload=True)
            st.rerun()

    # Quick Search Chips
    st.markdown("<small style='color:#94A3B8;'>Quick Queries:</small>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True):
        quick_query = "Which items do we need to reorder within 1 week based on current burn rate?"
    if c2.button("📦 Pending DO Status", use_container_width=True):
        quick_query = "Summarize our current pending Delivery Orders and backlog."
    if c3.button("🔄 Branch Transfer Needs", use_container_width=True):
        quick_query = "Check all warehouses and suggest immediate internal stock transfers."

    if "copilot_history" not in st.session_state:
        st.session_state.copilot_history = []

    # Render Chat History
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
            
            # Dynamic auto-detection of current generative model on active API key
            chosen_model = None
            try:
                available_models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                priority_list = [
                    "gemini-3.6-flash",
                    "gemini-3-flash-preview",
                    "gemini-2.5-flash",
                    "gemini-2.0-flash",
                    "gemini-1.5-flash"
                ]
                for cand in priority_list:
                    if cand in available_models:
                        chosen_model = cand
                        break
                if not chosen_model and available_models:
                    chosen_model = available_models[0]
            except Exception:
                chosen_model = "gemini-3.6-flash"

            model = genai.GenerativeModel(
                model_name=chosen_model or "gemini-3.6-flash",
                system_instruction=SYSTEM_PROMPT,
                tools=[query_sku_intelligence, query_reorder_recommendations, query_delivery_orders, get_global_kpis]
            )
            chat_session = model.start_chat(enable_automatic_function_calling=True)

            with st.spinner(f"Analyzing warehouse ledger ({chosen_model})..."):
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
        /* Pin button strictly to the bottom right */
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
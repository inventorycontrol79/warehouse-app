import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# =====================================================
# INDEPENDENT CLOUD FALLBACK & DATA INGESTION ENGINE
# =====================================================
def get_or_fetch_stock_data():
    """
    Ensures the Copilot has immediate access to live inventory data across
    all pages without requiring the user to visit the Tracking page first.
    """
    if "df_stock_live" in st.session_state and st.session_state.df_stock_live is not None and not st.session_state.df_stock_live.empty:
        return st.session_state.df_stock_live

    # Auto-load Worksheet 3 if uninitialized
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


def get_or_fetch_do_ledger():
    """Accesses active DO master dispatch data from Worksheet 0."""
    if "master_data" in st.session_state and not st.session_state.master_data.empty:
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
    """
    Looks up stock, facility distribution, daily velocities, and runway for specific SKUs.
    """
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
    for _, row in match.head(3).iterrows():
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


def query_delivery_orders(do_or_status_query: str) -> str:
    """
    Looks up DO numbers, customer statuses, and warehouse backlogs.
    """
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
    """
    Returns global operational KPIs across inventory and dispatch queues.
    """
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
   - When asked when to order, calculate remaining runway and deduct standard supplier lead time (14-21 days).
4. Tone & Style:
   - Crisp, analytical, executive, and structured with bold highlights and bullet points.
"""

# =====================================================
# UI INJECTION & MODAL LOGIC
# =====================================================
@st.dialog("🤖 Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    if "copilot_history" not in st.session_state:
        st.session_state.copilot_history = []

    for msg in st.session_state.copilot_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Ask about stock levels, reorders, DO status, or branch transfers...")
    if user_query:
        st.session_state.copilot_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools=[query_sku_intelligence, query_delivery_orders, get_global_kpis]
            )
            chat = model.start_chat(enable_automatic_function_calling=True)
            with st.spinner("Analyzing live inventory & velocity metrics..."):
                response = chat.send_message(user_query)
                answer = response.text
        except Exception as err:
            answer = f"🚨 Copilot Communication Issue: {err}"

        st.session_state.copilot_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)


def inject_floating_copilot():
    """Renders an animated, floating glassmorphism AI Copilot button in the bottom-right corner."""
    st.markdown("""
        <style>
        /* 1. Target the floating container and pin it strictly to the bottom-right viewport */
        div.element-container:has(button[key="floating_copilot_btn"]),
        div.stButton:has(button[key="floating_copilot_btn"]) {
            position: fixed !important;
            bottom: 24px !important;
            right: 28px !important;
            z-index: 9999999 !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 2. Premium Gradient & Glow Styling */
        button[key="floating_copilot_btn"] {
            background: linear-gradient(135deg, #0EA5E9 0%, #2563EB 50%, #4F46E5 100%) !important;
            color: #FFFFFF !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            border-radius: 50px !important;
            padding: 12px 26px !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            box-shadow: 0 8px 32px rgba(14, 165, 233, 0.45), 0 0 15px rgba(99, 102, 241, 0.35) !important;
            backdrop-filter: blur(8px) !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            animation: pulse-glow 3s infinite alternate !important;
        }

        /* 3. Interactive Hover State */
        button[key="floating_copilot_btn"]:hover {
            transform: translateY(-3px) scale(1.04) !important;
            background: linear-gradient(135deg, #38BDF8 0%, #3B82F6 50%, #6366F1 100%) !important;
            box-shadow: 0 12px 40px rgba(14, 165, 233, 0.65), 0 0 25px rgba(99, 102, 241, 0.55) !important;
            border-color: rgba(255, 255, 255, 0.5) !important;
            color: #FFFFFF !important;
        }

        /* 4. Active Click State */
        button[key="floating_copilot_btn"]:active {
            transform: translateY(1px) scale(0.98) !important;
        }

        /* 5. Subtle Ambient Glow Animation */
        @keyframes pulse-glow {
            0% {
                box-shadow: 0 8px 32px rgba(14, 165, 233, 0.35), 0 0 10px rgba(99, 102, 241, 0.25);
            }
            100% {
                box-shadow: 0 10px 38px rgba(14, 165, 233, 0.55), 0 0 22px rgba(99, 102, 241, 0.45);
            }
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Copilot AI", key="floating_copilot_btn"):
        render_copilot_modal()
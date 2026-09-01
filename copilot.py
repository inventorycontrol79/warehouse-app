import json
import re
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

# =====================================================
# FAST CLOUD CACHE & INGESTION ENGINE
# =====================================================
def get_or_fetch_stock_data(force_reload=False):
    """Retrieves live stock data with session cache to eliminate latency."""
    if not force_reload and "df_stock_live" in st.session_state and not st.session_state.df_stock_live.empty:
        return st.session_state.df_stock_live
    try:
        creds = Credentials.from_service_account_info(
            json.loads(st.secrets["GCP_JSON"]), 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        ws = gc.open_by_url(st.secrets["GSHEET_URL"]).get_worksheet(3)
        raw_data = ws.get_all_values()
        if raw_data:
            df = pd.DataFrame(raw_data[1:], columns=[str(h).strip() for h in raw_data[0]])
            st.session_state.df_stock_live = df.loc[:, ~df.columns.duplicated()].copy()
            return st.session_state.df_stock_live
    except Exception:
        pass
    return pd.DataFrame()


def get_or_fetch_do_ledger(force_reload=False):
    """Retrieves DO records with session-level caching."""
    if not force_reload and "master_data" in st.session_state and not st.session_state.master_data.empty:
        return st.session_state.master_data
    try:
        creds = Credentials.from_service_account_info(
            json.loads(st.secrets["GCP_JSON"]), 
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        ws = gc.open_by_url(st.secrets["GSHEET_URL"]).get_worksheet(0)
        df = pd.DataFrame(ws.get_all_records())
        st.session_state.master_data = df
        return df
    except Exception:
        return pd.DataFrame()

# =====================================================
# LOCAL ANALYTICS CONTEXT BUILDER
# =====================================================
def build_live_context(query: str) -> str:
    """Pre-calculates warehouse analytics locally using Pandas."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()
    if df_s.empty:
        return "System Notice: Live inventory dataset is unreachable."

    query_upper = query.upper()
    context_lines = []

    # 1. Targeted SKU search
    sku_matches = df_s[
        df_s['Item_Code'].astype(str).str.upper().apply(lambda x: x in query_upper if x else False) |
        df_s['Item_Name'].astype(str).str.upper().apply(lambda x: any(word in query_upper for word in str(x).split() if len(word) > 3))
    ]
    if not sku_matches.empty:
        context_lines.append("--- SPECIFIC SKU TELEMETRY ---")
        for _, r in sku_matches.head(4).iterrows():
            context_lines.append(
                f"SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | Total Stock: {r.get('Current_Stock')} | "
                f"Velocity: {r.get('Baseline_Velocity')}/day [SHJ: {r.get('Stock_Sharjah')}, AQ: {r.get('Stock_Al_Quoz')}, DIP: {r.get('Stock_DIP')}, AD: {r.get('Stock_Abu_Dhabi')}]"
            )

    df_s['Numeric_Stock'] = pd.to_numeric(df_s.get('Current_Stock', 0), errors='coerce').fillna(0)
    df_s['Numeric_Vel'] = pd.to_numeric(df_s.get('Baseline_Velocity', 0), errors='coerce').fillna(0)

    # 2. Inter-Branch Transfer Deficits & Surplus
    warehouse_cols = {
        "DIP": ("Stock_DIP", "Velocity_DIP"),
        "SHARJAH": ("Stock_Sharjah", "Velocity_Sharjah"),
        "AL QUOZ": ("Stock_Al_Quoz", "Velocity_Al_Quoz"),
        "ABU DHABI": ("Stock_Abu_Dhabi", "Velocity_Abu_Dhabi")
    }

    if any(k in query_upper for k in ["TRANSFER", "SHARJAH", "ABU DHABI", "AL QUOZ", "DIP", "MOVE"]):
        context_lines.append("\n--- NETWORK TRANSFER AUDIT ---")
        for wh, (stock_col, vel_col) in warehouse_cols.items():
            if stock_col in df_s.columns and vel_col in df_s.columns:
                df_s[f'Num_{stock_col}'] = pd.to_numeric(df_s[stock_col], errors='coerce').fillna(0)
                df_s[f'Num_{vel_col}'] = pd.to_numeric(df_s[vel_col], errors='coerce').fillna(0)

        # Evaluate Abu Dhabi deficits vs Sharjah surplus
        if "ABU DHABI" in query_upper or "SHARJAH" in query_upper:
            ad_critical = df_s[
                (df_s['Num_Velocity_Abu_Dhabi'] > 0.05) & 
                ((df_s['Num_Stock_Abu_Dhabi'] / df_s['Num_Velocity_Abu_Dhabi']) <= 7.0)
            ]
            for _, r in ad_critical.head(8).iterrows():
                ad_runway = round(r['Num_Stock_Abu_Dhabi'] / r['Num_Velocity_Abu_Dhabi'], 1) if r['Num_Velocity_Abu_Dhabi'] > 0 else 0
                shj_stock = r.get('Num_Stock_Sharjah', 0)
                shj_vel = r.get('Num_Velocity_Sharjah', 0)
                shj_safe = int(shj_stock - (14.0 * shj_vel)) if shj_vel > 0 else int(shj_stock)

                context_lines.append(
                    f"SKU {r.get('Item_Code')} ({r.get('Item_Name')}): "
                    f"Abu Dhabi Stock={r.get('Num_Stock_Abu_Dhabi')} (Runway: {ad_runway}d, Burn: {r.get('Num_Velocity_Abu_Dhabi')}/d) | "
                    f"Sharjah Stock={shj_stock} (Safe Donor Capacity: {max(0, shj_safe)} units)"
                )

    # 3. Critical Runway Items (< 7 days network-wide)
    if any(k in query_upper for k in ["REORDER", "RUNWAY", "DEFICIT", "STOCK OUT", "CRITICAL"]):
        context_lines.append("\n--- NETWORK CRITICAL RUNWAY (< 7 DAYS) ---")
        urgent = df_s[(df_s['Numeric_Vel'] > 0.05) & ((df_s['Numeric_Stock'] / df_s['Numeric_Vel']) <= 7.0)]
        for _, r in urgent.head(8).iterrows():
            runway = round(r['Numeric_Stock'] / r['Numeric_Vel'], 1) if r['Numeric_Vel'] > 0 else 999
            context_lines.append(
                f"ALERT: SKU {r.get('Item_Code')} ({r.get('Item_Name')}) -> Total Stock {r['Numeric_Stock']} units | Runway {runway} days"
            )

    # 4. Delivery Orders Overview
    if any(k in query_upper for k in ["DO", "PENDING", "DISPATCH", "ORDER", "BACKLOG"]):
        context_lines.append("\n--- ACTIVE DELIVERY ORDER TELEMETRY ---")
        if not df_do.empty and "Status" in df_do.columns:
            pending = df_do[df_do['Status'].astype(str).str.upper() == 'PENDING']
            context_lines.append(f"Total Pending DO Backlog: {len(pending)} orders")
            for _, d in pending.head(5).iterrows():
                context_lines.append(f"DO #{d.get('DO_Number')} | Facility: {d.get('Warehouse_Name')} | Date: {d.get('Date_Issued')}")

    return "\n".join(context_lines)

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer & Senior Logistics Analyst for Sabin Plastic.
You analyze inventory distribution across Sharjah, Al Quoz, DIP, and Abu Dhabi.

Directives:
1. Grounding: Answer strictly using data inside 'LOCAL CONTEXT'. Do not invent SKUs or numbers.
2. Inter-Branch Stock Transfers:
   - Identify deficit branches (<= 7 days runway) and donor branches with surplus stock.
   - For every transfer, provide the exact Focus ERP execution command:
     `SRTS: Move [Qty] units of SKU [SKU] from [Donor Warehouse] to [Destination Warehouse]`
3. Presentation:
   - Present transfer plans and runway analyses using clean Markdown Tables.
   - Use bold highlights for SKUs, quantities, and urgency levels.
   - Never output internal monologue, thought tags, or meta-commentary.
"""

# =====================================================
# UI INJECTION & STATE-MANAGED MODAL LOGIC
# =====================================================
@st.dialog("Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    st.markdown("""
        <style>
        /* 1. HIDE DEFAULT DIALOG CLOSE BUTTON */
        div[data-testid="stDialog"] button[aria-label="Close"],
        div[data-baseweb="modal"] button[aria-label="Close"] {
            display: none !important;
        }

        /* 2. BASEWEB ROOT MODAL - MIDNIGHT NAVY THEME */
        div[data-baseweb="modal"],
        div[data-baseweb="modal"] > div,
        div[data-baseweb="modal"] [role="dialog"],
        div[data-testid="stDialog"],
        div[data-testid="stDialog"] [role="dialog"],
        div[data-testid="stModal"] [role="dialog"] {
            background-color: #070B14 !important;
            background: linear-gradient(160deg, #0A0F1D 0%, #040711 100%) !important;
            color: #F1F5F9 !important;
        }

        /* 3. MODAL SURROUND BORDER & GLOW */
        div[data-baseweb="modal"] [role="dialog"],
        div[data-testid="stDialog"] [role="dialog"] {
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
            border-radius: 18px !important;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.85), 0 0 35px rgba(56, 189, 248, 0.15) !important;
            overflow: hidden !important;
        }

        /* 4. TRANSPARENT STRUCTURAL WRAPPERS */
        div[data-testid="stDialog"] [data-testid="stVerticalBlock"],
        div[data-baseweb="modal"] [data-testid="stVerticalBlock"] {
            background: transparent !important;
        }

        /* 5. EXECUTIVE HEADER */
        div[data-testid="stDialog"] header,
        div[data-baseweb="modal"] header {
            background: transparent !important;
            border-bottom: 1px solid rgba(56, 189, 248, 0.2) !important;
            min-height: 48px !important;
            margin-bottom: 14px !important;
        }

        div[data-testid="stDialog"] h2,
        div[data-baseweb="modal"] h2 {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            color: #FFFFFF !important;
            font-size: 22px !important;
            font-weight: 800 !important;
            letter-spacing: 0.75px !important;
            text-transform: uppercase !important;
            text-shadow: 0 0 16px rgba(56, 189, 248, 0.6), 0 0 32px rgba(56, 189, 248, 0.25) !important;
        }

        div[data-testid="stDialog"] h2::before,
        div[data-baseweb="modal"] h2::before {
            content: "✦ ";
            color: #38BDF8 !important;
            text-shadow: 0 0 20px #38BDF8 !important;
        }

        /* 6. CHAT INPUT CONTAINER */
        div[data-testid="stChatInput"], 
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] div[data-baseweb="textarea"] { 
            background-color: #0F172A !important; 
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            border-radius: 12px !important;
        }
        div[data-testid="stChatInput"] textarea { 
            color: #FFFFFF !important; 
            -webkit-text-fill-color: #FFFFFF !important; 
            background-color: transparent !important; 
            caret-color: #38BDF8 !important; 
        }
        div[data-testid="stChatInput"] textarea::placeholder { 
            color: #94A3B8 !important; 
            -webkit-text-fill-color: #94A3B8 !important; 
        }
        div[data-testid="stChatInput"] button { 
            color: #38BDF8 !important; 
        }

        /* 7. CHAT MESSAGE CARDS & SCOPED TYPOGRAPHY (Fixes Broken Icons) */
        div[data-testid="stChatMessage"] { 
            background-color: #0F172A !important; 
            border-radius: 12px !important; 
            padding: 16px !important; 
            border: 1px solid rgba(51, 65, 85, 0.8) !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li,
        div[data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"] {
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
            padding: 2px 6px !important;
            border-radius: 4px !important;
        }

        /* Table Styling inside Messages */
        div[data-testid="stChatMessage"] table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin: 12px 0 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
        }
        div[data-testid="stChatMessage"] th {
            background-color: #1E293B !important;
            color: #38BDF8 !important;
            padding: 8px 12px !important;
            font-weight: 700 !important;
            border: 1px solid #334155 !important;
            font-size: 13px !important;
        }
        div[data-testid="stChatMessage"] td {
            background-color: #0B1120 !important;
            color: #F1F5F9 !important;
            padding: 8px 12px !important;
            border: 1px solid #1E293B !important;
            font-size: 13px !important;
        }

        /* 8. ACTION BUTTONS & CHIPS */
        div[data-testid="stDialog"] div[data-testid="stButton"] button { 
            background-color: #1E293B !important; 
            color: #F8FAFC !important; 
            border: 1px solid #334155 !important; 
            font-weight: 600 !important; 
            border-radius: 8px !important; 
            transition: all 0.25s ease !important; 
        }
        div[data-testid="stDialog"] div[data-testid="stButton"] button:hover { 
            background-color: #0EA5E9 !important; 
            color: #020617 !important; 
            border-color: #38BDF8 !important; 
        }

        /* 9. RED CLOSE BUTTON */
        .custom-close-btn button {
            background-color: #DC2626 !important;
            color: #FFFFFF !important;
            border-color: #EF4444 !important;
        }
        .custom-close-btn button:hover {
            background-color: #B91C1C !important;
            color: #FFFFFF !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header Control Bar
    col_reset, col_close = st.columns([8, 2])
    with col_reset:
        if st.button("🗑️ Reset Engine & Sync Database", use_container_width=True):
            st.session_state.copilot_history = []
            get_or_fetch_stock_data(force_reload=True)
            get_or_fetch_do_ledger(force_reload=True)
            st.rerun()
    with col_close:
        st.markdown('<div class="custom-close-btn">', unsafe_allow_html=True)
        if st.button("❌ Close", use_container_width=True):
            st.session_state.copilot_open = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Action Chips
    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True): 
        quick_query = "Which items do we need to reorder within 1 week?"
    if c2.button("📦 Pending DO Status", use_container_width=True): 
        quick_query = "Summarize our current pending Delivery Orders."
    if c3.button("🔄 Sharjah → Abu Dhabi Transfers", use_container_width=True): 
        quick_query = "Which are the SKUs I need to transfer from Sharjah to Abu Dhabi?"

    if "copilot_history" not in st.session_state: 
        st.session_state.copilot_history = []

    # Render History with Explicit Avatars (Prevents Text Ligature Artifacts)
    for msg in st.session_state.copilot_history:
        avatar_icon = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # Executive Telemetry Badge
    st.markdown("""
    <div style="
    background: linear-gradient(90deg, #0F172A, #1E293B);
    padding: 12px 18px;
    border-radius: 12px;
    border: 1px solid rgba(56, 189, 248, 0.25);
    margin-bottom: 12px;
    font-size: 13px;
    font-weight: 600;
    color: #38BDF8;
    ">
    ⚡ AI Inventory Intelligence • Real-Time Warehouse Analytics • Powered by Groq
    </div>
    """, unsafe_allow_html=True)

    user_input = st.chat_input("Ask about stock levels, reorders, DO status, or branch transfers...")
    query_to_process = quick_query if quick_query else user_input

    if query_to_process:
        st.session_state.copilot_history.append({"role": "user", "content": query_to_process})
        with st.chat_message("user", avatar="👤"):
            st.markdown(query_to_process)

        try:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            
            with st.spinner("Analyzing warehouse telemetry..."):
                local_context = build_live_context(query_to_process)
                final_prompt = f"LOCAL CONTEXT:\n{local_context}\n\nUSER QUESTION:\n{query_to_process}"
                
                # Fetch active model list
                live_models = client.models.list().data
                valid_model_ids = [m.id for m in live_models if "whisper" not in m.id.lower() and "guard" not in m.id.lower()]
                
                if not valid_model_ids:
                    raise ValueError("No active text models found for this Groq API Key.")

                target_model = valid_model_ids[0]
                for pref in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                    if pref in valid_model_ids:
                        target_model = pref
                        break

                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": final_prompt}
                    ],
                    model=target_model,
                    temperature=0.1,
                    max_tokens=1024
                )
                raw_response = chat_completion.choices[0].message.content

                # Regex Thought-Sanitization Pipeline: Strips any <think> scratchpad
                cleaned_answer = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL).strip()
                if not cleaned_answer:
                    cleaned_answer = raw_response.strip()

        except Exception as err:
            if "429" in str(err):
                cleaned_answer = "⏳ **API Rate Limit Notice:** Please wait 10-20 seconds before asking another question."
            else:
                cleaned_answer = f"⚠️ **System Notice:** {err}"

        st.session_state.copilot_history.append({"role": "assistant", "content": cleaned_answer})
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(cleaned_answer)


def inject_floating_copilot():
    """Renders the AI Copilot floating trigger button."""
    if "copilot_open" not in st.session_state:
        st.session_state.copilot_open = False

    st.markdown("""
        <style>
        .st-key-floating_copilot_btn {
            position: fixed !important;
            bottom: 95px !important;
            right: 30px !important;
            z-index: 2147483647 !important;
        }

        .st-key-floating_copilot_btn > button {
            background: linear-gradient(
                135deg,
                #0EA5E9 0%,
                #2563EB 45%,
                #4F46E5 100%
            ) !important;
            color: white !important;
            border: none !important;
            border-radius: 60px !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            padding: 16px 32px !important;
            box-shadow: 
                0 12px 30px rgba(37,99,235,0.35),
                0 0 25px rgba(56,189,248,0.25) !important;
            transition: all 0.35s ease !important;
            position: relative !important;
            overflow: hidden !important;
        }

        /* Light Sweep Animation */
        .st-key-floating_copilot_btn > button::before {
            content: "";
            position: absolute;
            top: 0;
            left: -120%;
            width: 60%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255,255,255,0.4),
                transparent
            );
            transform: skewX(-20deg);
            animation: sweep 4s infinite;
        }

        @keyframes sweep {
            0% { left: -120%; }
            100% { left: 140%; }
        }

        .st-key-floating_copilot_btn > button:hover {
            transform: translateY(-5px) scale(1.04) !important;
            box-shadow: 
                0 18px 40px rgba(37,99,235,0.45),
                0 0 40px rgba(56,189,248,0.4) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Ask Copilot", key="floating_copilot_btn"):
        st.session_state.copilot_open = True
        st.rerun()

    if st.session_state.copilot_open:
        render_copilot_modal()
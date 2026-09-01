import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

# =====================================================
# FAST CLOUD CACHE & INGESTION ENGINE
# =====================================================
def get_or_fetch_stock_data(force_reload=False):
    """Retrieves live stock data with session cache to eliminate round-trip latency."""
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
# HIGH-SPEED LOCAL CONTEXT BUILDER
# =====================================================
def build_live_context(query: str) -> str:
    """Pre-calculates warehouse analytics locally using Pandas to minimize token load and API latency."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()
    if df_s.empty:
        return "System Notice: Live inventory dataset is unreachable."

    query_upper = query.upper()
    context_lines = []

    sku_matches = df_s[
        df_s['Item_Code'].astype(str).str.upper().apply(lambda x: x in query_upper if x else False) |
        df_s['Item_Name'].astype(str).str.upper().apply(lambda x: any(word in query_upper for word in str(x).split() if len(word) > 3))
    ]
    if not sku_matches.empty:
        context_lines.append("--- SPECIFIC SKU MATCHES ---")
        for _, r in sku_matches.head(4).iterrows():
            context_lines.append(
                f"SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | Total Stock: {r.get('Current_Stock')} | "
                f"Velocity: {r.get('Baseline_Velocity')}/day [SHJ: {r.get('Stock_Sharjah')}, AQ: {r.get('Stock_Al_Quoz')}, DIP: {r.get('Stock_DIP')}, AD: {r.get('Stock_Abu_Dhabi')}]"
            )

    df_s['Numeric_Stock'] = pd.to_numeric(df_s.get('Current_Stock', 0), errors='coerce').fillna(0)
    df_s['Numeric_Vel'] = pd.to_numeric(df_s.get('Baseline_Velocity', 0), errors='coerce').fillna(0)

    warehouse_cols = {
        "DIP": "Velocity_DIP",
        "SHARJAH": "Velocity_Sharjah",
        "AL QUOZ": "Velocity_Al_Quoz",
        "ABU DHABI": "Velocity_Abu_Dhabi"
    }
    
    for wh_name, vel_col in warehouse_cols.items():
        if wh_name in query_upper or "MOVER" in query_upper or "BEST" in query_upper:
            if vel_col in df_s.columns:
                df_s[f'Num_{vel_col}'] = pd.to_numeric(df_s[vel_col], errors='coerce').fillna(0)
                top_movers = df_s.sort_values(by=f'Num_{vel_col}', ascending=False).head(5)
                context_lines.append(f"\n--- TOP MOVING ITEMS IN {wh_name} ---")
                for _, r in top_movers.iterrows():
                    context_lines.append(
                        f"SKU {r.get('Item_Code')} ({r.get('Item_Name')}): Velocity = {r.get(f'Num_{vel_col}')} units/day | Warehouse Stock = {r.get(f'Stock_{vel_col.replace('Velocity_', '')}')}"
                    )

    if any(k in query_upper for k in ["REORDER", "TRANSFER", "RUNWAY", "DEFICIT", "STOCK OUT"]):
        context_lines.append("\n--- CRITICAL RUNWAY (< 7 DAYS) & TRANSFER DEFICITS ---")
        urgent = df_s[(df_s['Numeric_Vel'] > 0.05) & ((df_s['Numeric_Stock'] / df_s['Numeric_Vel']) <= 7.0)]
        for _, r in urgent.head(10).iterrows():
            runway = round(r['Numeric_Stock'] / r['Numeric_Vel'], 1) if r['Numeric_Vel'] > 0 else 999
            context_lines.append(
                f"CRITICAL: {r.get('Item_Code')} ({r.get('Item_Name')}) -> {runway} days runway. "
                f"[Total: {r['Numeric_Stock']}, SHJ: {r.get('Stock_Sharjah', 0)}, AQ: {r.get('Stock_Al_Quoz', 0)}, DIP: {r.get('Stock_DIP', 0)}, AD: {r.get('Stock_Abu_Dhabi', 0)}]"
            )

    if any(k in query_upper for k in ["DO", "PENDING", "DISPATCH", "ORDER"]):
        context_lines.append("\n--- ACTIVE DELIVERY ORDER TELEMETRY ---")
        if not df_do.empty and "Status" in df_do.columns:
            pending = df_do[df_do['Status'].astype(str).str.upper() == 'PENDING']
            context_lines.append(f"Total Pending DOs in Backlog: {len(pending)}")
            for _, d in pending.head(6).iterrows():
                context_lines.append(f"DO #{d.get('DO_Number')} | Facility: {d.get('Warehouse_Name')} | Date: {d.get('Date_Issued')} | Remarks: {d.get('Remarks', 'None')}")

    return "\n".join(context_lines)

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer & Senior Logistics Analyst for Sabin Plastic.
You have direct access to live inventory positions across Sharjah, Al Quoz, DIP, and Abu Dhabi facilities.

Core Rules:
1. Grounding: Answer strictly using the provided 'LOCAL CONTEXT' telemetry.
2. Inter-Branch Stock Transfers:
   - When suggesting stock movements to balance deficits, provide the exact Focus ERP command:
     `SRTS: Move [Qty] units of SKU [SKU] from [Donor Warehouse] to [Destination Warehouse]`
3. Reorders: Rank urgency based on shortest runway (Days of Coverage = Current Stock / Daily Velocity).
4. Tone & Presentation: Crisp, corporate, structured with bold highlights, bullet points, and concise numbers.
"""

# =====================================================
# UI INJECTION & STATE-MANAGED MODAL LOGIC
# =====================================================
@st.dialog("🤖 Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    st.markdown("""
        <style>
        /* 1. Hide the native Streamlit dialog close (X) button to prevent state desync */
        div[data-testid="stDialog"] button[aria-label="Close"] {
            display: none !important;
        }

        /* 2. Glassmorphism Modal Surface — force Streamlit's own theme variables
           so every child component (headings, captions, markdown) that reads
           var(--text-color)/var(--background-color) internally inherits the
           correct dark-mode values regardless of Streamlit version/DOM changes. */
        div[role="dialog"] {
            --text-color: #F8FAFC;
            --background-color: #0B0F19;
            --secondary-background-color: #1E293B;
            background-color: #0B0F19 !important;
            color: #F8FAFC !important;
            border: 1px solid #38BDF8 !important; 
            border-radius: 16px !important; 
            box-shadow: 0 10px 40px rgba(56, 189, 248, 0.15) !important;
        }

        /* SAFETY NET: force every text node inside the dialog to a readable
           light color, so nothing can silently fall back to white-on-white. */
        div[role="dialog"] * {
            color: #F8FAFC !important;
        }

        /* 2b. Header strip — MUST stay dark. Leaving this transparent lets the
           white page behind the dialog show through and makes the title
           unreadable, so it is pinned to the same navy as the modal surface. */
        div[data-testid="stDialog"] header,
        div[role="dialog"] > div:first-child { 
            background-color: #0B0F19 !important; 
        }

        /* Modal Title — multiple fallback selectors across Streamlit versions */
        div[data-testid="stDialog"] h2, 
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"] *,
        div[role="dialog"] h2,
        div[role="dialog"] [data-testid="stMarkdownContainer"] h2 { 
            color: #38BDF8 !important; 
            font-weight: 800 !important; 
            font-size: 22px !important;
        }

        /* Caption row */
        div[role="dialog"] [data-testid="stCaptionContainer"],
        div[role="dialog"] [data-testid="stCaptionContainer"] * {
            color: #94A3B8 !important;
            font-weight: 500 !important;
        }
        
        /* 3. Bulletproof Chat Input Text Color (Fixes White-on-White) */
        div[data-testid="stChatInput"], 
        div[data-testid="stChatInput"] > div,
        div[data-testid="stChatInput"] div[data-baseweb="textarea"] { 
            background-color: #0F172A !important; 
        }
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] [contenteditable="true"] { 
            color: #FFFFFF !important; 
            -webkit-text-fill-color: #FFFFFF !important; 
            background-color: #0F172A !important; 
            caret-color: #38BDF8 !important; 
        }
        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] [contenteditable="true"]:empty::before { 
            color: #94A3B8 !important; 
            -webkit-text-fill-color: #94A3B8 !important; 
        }
        div[data-testid="stChatInput"] button { 
            color: #38BDF8 !important; 
        }
        
        /* 4. Chat Bubbles */
        div[data-testid="stChatMessage"] { 
            background-color: #1E293B !important; 
            border-radius: 12px !important; 
            padding: 15px !important; 
            border: 1px solid #334155 !important;
        }
        div[data-testid="stChatMessage"] * { 
            color: #F8FAFC !important; 
        }
        div[data-testid="stChatMessage"] strong { 
            color: #38BDF8 !important; 
        }
        div[data-testid="stChatMessage"] code { 
            color: #38BDF8 !important; 
            background-color: #020617 !important; 
            border: 1px solid #1E293B !important; 
        }
        
        /* 5. Custom Standard Buttons */
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
        
        /* 6. Custom Red Close Button */
        .custom-close-btn button {
            background-color: #EF4444 !important;
            color: #FFFFFF !important;
            border-color: #EF4444 !important;
        }
        .custom-close-btn button:hover {
            background-color: #DC2626 !important;
            color: #FFFFFF !important;
            border-color: #B91C1C !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Custom Header Control Bar
    col_title, col_reset, col_close = st.columns([4, 2, 2])
    with col_title:
        st.caption("⚡ Groq Engine: Ultra-Fast Data Processing")
    with col_reset:
        if st.button("🗑️ Reset", use_container_width=True):
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

    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True): 
        quick_query = "Which items do we need to reorder within 1 week?"
    if c2.button("📦 Pending DO Status", use_container_width=True): 
        quick_query = "Summarize our current pending Delivery Orders."
    if c3.button("🔄 DIP Best Movers", use_container_width=True): 
        quick_query = "Which are the best moving items in the DIP warehouse?"

    if "copilot_history" not in st.session_state: 
        st.session_state.copilot_history = []

    # Display Conversation History
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
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            
            with st.spinner("Analyzing warehouse telemetry..."):
                local_context = build_live_context(query_to_process)
                final_prompt = f"LOCAL CONTEXT:\n{local_context}\n\nUSER QUESTION:\n{query_to_process}"
                
                # Fetch EXACT list of active models directly from Groq to prevent 404s
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
                answer = chat_completion.choices[0].message.content

        except Exception as err:
            if "429" in str(err):
                answer = "⏳ **API Rate Limit Notice:** You've reached your free Groq limit. Please wait 10-30 seconds before asking another question."
            else:
                answer = f"⚠️ **System Notice:** {err}"

        st.session_state.copilot_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)


def inject_floating_copilot():
    """Renders the AI Copilot button and manages its open/closed state safely."""
    
    # Initialize state
    if "copilot_open" not in st.session_state:
        st.session_state.copilot_open = False

    # Premium Expressive Corporate UI with Glassmorphism
    st.markdown("""
        <style>
        .st-key-floating_copilot_btn { 
            position: fixed !important; 
            bottom: 100px !important; /* Elevated safely above the Manage App logo */
            right: 30px !important; 
            z-index: 2147483647 !important; 
        }
        .st-key-floating_copilot_btn > button { 
            background: linear-gradient(135deg, #0EA5E9 0%, #3B82F6 100%) !important;
            color: #FFFFFF !important; 
            font-family: 'Inter', sans-serif !important;
            font-size: 16px !important; 
            font-weight: 800 !important; 
            border-radius: 50px !important; 
            padding: 16px 32px !important; 
            border: 2px solid rgba(255, 255, 255, 0.2) !important; 
            box-shadow: 0 10px 30px rgba(14, 165, 233, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3) !important; 
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; 
            animation: premiumPulse 2.5s infinite alternate !important;
        }
        .st-key-floating_copilot_btn > button:hover { 
            transform: translateY(-8px) scale(1.05) !important; 
            box-shadow: 0 15px 40px rgba(14, 165, 233, 0.6), inset 0 2px 5px rgba(255, 255, 255, 0.4) !important; 
            border-color: rgba(255, 255, 255, 0.5) !important;
        }
        
        @keyframes premiumPulse {
            0% { filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.4)); }
            100% { filter: drop-shadow(0 0 25px rgba(56, 189, 248, 0.8)); }
        }
        </style>
    """, unsafe_allow_html=True)

    # When clicked, update state and trigger a rerun
    if st.button("✨ Ask Copilot", key="floating_copilot_btn"):
        st.session_state.copilot_open = True
        st.rerun()

    # The dialog is exclusively driven by state. It will survive background auto-refreshes.
    if st.session_state.copilot_open:
        render_copilot_modal()
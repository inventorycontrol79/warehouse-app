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

    # 1. Look for specific SKU matches in the prompt
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

    # Convert numeric fields for accurate analytics
    df_s['Numeric_Stock'] = pd.to_numeric(df_s.get('Current_Stock', 0), errors='coerce').fillna(0)
    df_s['Numeric_Vel'] = pd.to_numeric(df_s.get('Baseline_Velocity', 0), errors='coerce').fillna(0)

    # 2. Warehouse Best Movers Analysis
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

    # 3. Critical Runway & Transfer Logic (< 7 days)
    if any(k in query_upper for k in ["REORDER", "TRANSFER", "RUNWAY", "DEFICIT", "STOCK OUT"]):
        context_lines.append("\n--- CRITICAL RUNWAY (< 7 DAYS) & TRANSFER DEFICITS ---")
        urgent = df_s[(df_s['Numeric_Vel'] > 0.05) & ((df_s['Numeric_Stock'] / df_s['Numeric_Vel']) <= 7.0)]
        for _, r in urgent.head(10).iterrows():
            runway = round(r['Numeric_Stock'] / r['Numeric_Vel'], 1) if r['Numeric_Vel'] > 0 else 999
            context_lines.append(
                f"CRITICAL: {r.get('Item_Code')} ({r.get('Item_Name')}) -> {runway} days runway. "
                f"[Total: {r['Numeric_Stock']}, SHJ: {r.get('Stock_Sharjah', 0)}, AQ: {r.get('Stock_Al_Quoz', 0)}, DIP: {r.get('Stock_DIP', 0)}, AD: {r.get('Stock_Abu_Dhabi', 0)}]"
            )

    # 4. Delivery Orders Overview
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
# UI INJECTION & MODAL LOGIC
# =====================================================
@st.dialog("🤖 Sabin Intelligence Copilot", width="large")
def render_copilot_modal():
    st.markdown("""
        <style>
        /* Dialog Modal Surface */
        div[data-testid="stDialog"] div[role="dialog"] { 
            background-color: #0B0F19 !important; 
            border: 1px solid #1E293B !important; 
            border-radius: 16px !important; 
        }
        div[data-testid="stDialog"] header { 
            background-color: #0B0F19 !important; 
        }

        /* SAFETY NET: force every text node inside the dialog to a readable
           light color first, so nothing can silently inherit white-on-white
           from Streamlit's base theme. More specific rules below override this. */
        div[data-testid="stDialog"] * {
            color: #F8FAFC !important;
        }

        /* Modal Title (covers the actual header text node across Streamlit versions) */
        div[data-testid="stDialog"] h2,
        div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"] *,
        div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] h2 { 
            color: #38BDF8 !important; 
            font-weight: 800 !important; 
            font-size: 20px !important;
        }

        /* Caption row ("⚡ Direct Engine: ...") */
        div[data-testid="stDialog"] [data-testid="stCaptionContainer"],
        div[data-testid="stDialog"] [data-testid="stCaptionContainer"] * {
            color: #94A3B8 !important;
            font-weight: 500 !important;
        }
        
        /* Action Buttons & Quick Filter Chips */
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
        div[data-testid="stDialog"] div[data-testid="stButton"] button p { 
            color: inherit !important; 
        }
        
        /* Chat History Bubbles */
        div[data-testid="stChatMessage"] { 
            background-color: #111827 !important; 
            border: 1px solid #1E293B !important; 
            border-radius: 12px !important; 
            margin-bottom: 12px !important; 
            padding: 14px !important; 
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
        
        /* High-Contrast Chat Input (covers the wrapper div, the textarea itself,
           and any contenteditable/base-web layer Streamlit renders the typed
           value through) */
        div[data-testid="stChatInput"],
        div[data-testid="stChatInput"] > div { 
            background-color: #0F172A !important; 
            border: 1px solid #334155 !important; 
            border-radius: 12px !important; 
        }
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] [contenteditable="true"],
        div[data-testid="stChatInput"] [data-baseweb="textarea"],
        div[data-testid="stChatInput"] [data-baseweb="textarea"] * { 
            color: #FFFFFF !important; 
            -webkit-text-fill-color: #FFFFFF !important; 
            background-color: transparent !important; 
            caret-color: #38BDF8 !important; 
        }
        div[data-testid="stChatInput"] textarea::placeholder,
        div[data-testid="stChatInput"] [contenteditable="true"]:empty::before { 
            color: #64748B !important; 
            -webkit-text-fill-color: #64748B !important; 
        }
        div[data-testid="stChatInput"] button svg { 
            fill: #38BDF8 !important; 
            color: #38BDF8 !important; 
        }
        </style>
    """, unsafe_allow_html=True)

    col_hdr, col_clear = st.columns([3, 1])
    with col_hdr:
        st.caption("⚡ Direct Engine: Active Inventory, Demand Velocities & Dispatch Queues")
    with col_clear:
        if st.button("🗑️ Reset & Sync", use_container_width=True, help="Clear history and reload latest Google Sheets records"):
            st.session_state.copilot_history = []
            get_or_fetch_stock_data(force_reload=True)
            get_or_fetch_do_ledger(force_reload=True)
            st.rerun()

    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True): 
        quick_query = "Which items do we need to reorder within 1 week based on current burn rate?"
    if c2.button("📦 Pending DO Status", use_container_width=True): 
        quick_query = "Summarize our current pending Delivery Orders and backlog."
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
                
                # Fetch EXACT list of models currently online and assigned to your key
                live_models = client.models.list().data
                
                # Filter out audio/whisper/guardrail models to get pure text LLMs
                valid_model_ids = [m.id for m in live_models if "whisper" not in m.id.lower() and "guard" not in m.id.lower()]
                
                if not valid_model_ids:
                    raise ValueError("No active text models found for this Groq API Key.")

                # Pick the best model from the actual live list
                target_model = valid_model_ids[0] # Default to whatever is online
                for pref in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                    if pref in valid_model_ids:
                        target_model = pref
                        break

                # Execute exactly ONE call to expose the true error (like Rate Limits) if it fails
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
    """Renders a premium animated glassmorphism Copilot orb above the Streamlit footer.
    Idles as a breathing, softly pulsing circular orb with an orbiting sparkle.
    On hover it blooms into a full pill, revealing the 'Ask Copilot' label."""
    st.markdown("""
        <style>
        .st-key-floating_copilot_btn { 
            position: fixed !important; 
            bottom: 85px !important; 
            right: 30px !important; 
            z-index: 2147483647 !important; 
            width: auto !important; 
        }

        /* Outer pulse ring, sits behind the button and breathes independently */
        .st-key-floating_copilot_btn::before {
            content: "";
            position: absolute;
            inset: -6px;
            border-radius: 50px;
            background: linear-gradient(135deg, rgba(56,189,248,0.55), rgba(14,165,233,0.15));
            filter: blur(10px);
            z-index: -1;
            animation: copilotPulseRing 2.6s ease-in-out infinite;
            pointer-events: none;
        }

        .st-key-floating_copilot_btn > button { 
            position: relative;
            background: linear-gradient(160deg, rgba(15,23,42,0.94), rgba(11,15,25,0.98)) !important; 
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            color: #E0F2FE !important; 
            font-family: 'Inter', sans-serif !important;
            font-size: 14px !important; 
            font-weight: 700 !important; 
            letter-spacing: 0.5px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            border-radius: 50px !important; 
            width: 58px !important;
            height: 58px !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border: 1px solid rgba(56, 189, 248, 0.45) !important; 
            box-shadow: 0 0 18px rgba(56, 189, 248, 0.28), inset 0 0 18px rgba(56, 189, 248, 0.08) !important; 
            transition: width 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275),
                        padding 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.275),
                        transform 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275),
                        box-shadow 0.35s ease,
                        border-color 0.35s ease !important; 
            animation: copilotFloat 3.4s ease-in-out infinite !important;
        }

        /* Sparkle + label are one text node from st.button; this keeps the
           whole thing centered and lets width do the reveal/hide work */
        .st-key-floating_copilot_btn > button p {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }

        .st-key-floating_copilot_btn > button:hover { 
            width: 190px !important;
            padding: 12px 24px !important;
            transform: translateY(-6px) scale(1.04) !important; 
            background: linear-gradient(160deg, rgba(15,23,42,0.99), rgba(2,6,23,1)) !important; 
            border: 1px solid rgba(56, 189, 248, 0.95) !important;
            box-shadow: 0 14px 34px rgba(56, 189, 248, 0.4), 0 0 26px rgba(56, 189, 248, 0.4) !important; 
            color: #FFFFFF !important; 
            animation-play-state: paused !important;
        }

        .st-key-floating_copilot_btn > button:active {
            transform: translateY(-2px) scale(0.98) !important;
        }

        /* Gentle breathing float while idle */
        @keyframes copilotFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
        }

        /* Outer glow ring breathing, offset timing from the float for a
           layered "alive" premium feel */
        @keyframes copilotPulseRing {
            0%, 100% { opacity: 0.55; transform: scale(1); }
            50% { opacity: 0.15; transform: scale(1.18); }
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Ask Copilot", key="floating_copilot_btn"):
        render_copilot_modal()
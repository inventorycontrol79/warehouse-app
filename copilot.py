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
    """Pre-calculates warehouse math locally using Pandas to save API calls."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()
    if df_s.empty:
        return "System Notice: Live stock data is unreachable."

    query_upper = query.upper()
    context_lines = []

    sku_matches = df_s[
        df_s['Item_Code'].astype(str).str.upper().apply(lambda x: x in query_upper) |
        df_s['Item_Name'].astype(str).str.upper().apply(lambda x: any(word in query_upper for word in x.split() if len(word)>3))
    ]
    if not sku_matches.empty:
        context_lines.append("--- SPECIFIC SKU MATCHES ---")
        for _, r in sku_matches.head(3).iterrows():
            context_lines.append(f"SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | Total Stock: {r.get('Current_Stock')} | Velocity: {r.get('Baseline_Velocity')}/day")

    if "REORDER" in query_upper or "TRANSFER" in query_upper or "ABU DHABI" in query_upper or "DIP" in query_upper:
        context_lines.append("\n--- CRITICAL RUNWAY (< 7 DAYS) & TRANSFER RECS ---")
        df_s['Numeric_Stock'] = pd.to_numeric(df_s.get('Current_Stock', 0), errors='coerce').fillna(0)
        df_s['Numeric_Vel'] = pd.to_numeric(df_s.get('Baseline_Velocity', 0), errors='coerce').fillna(0)
        
        urgent = df_s[(df_s['Numeric_Vel'] > 0.05) & ((df_s['Numeric_Stock'] / df_s['Numeric_Vel']) <= 7.0)]
        for _, r in urgent.head(10).iterrows():
            runway = round(r['Numeric_Stock'] / r['Numeric_Vel'], 1) if r['Numeric_Vel'] > 0 else 999
            context_lines.append(
                f"ALERT: {r.get('Item_Code')} ({r.get('Item_Name')}) has {runway} days left. "
                f"(Stock: {r['Numeric_Stock']}, AQ: {r.get('Stock_Al_Quoz', 0)}, AD: {r.get('Stock_Abu_Dhabi', 0)}, SHJ: {r.get('Stock_Sharjah', 0)}, DIP: {r.get('Stock_DIP', 0)})"
            )

    if "DO" in query_upper or "PENDING" in query_upper:
        context_lines.append("\n--- PENDING DELIVERY ORDERS ---")
        if not df_do.empty and "Status" in df_do.columns:
            pending = df_do[df_do['Status'].astype(str).str.upper() == 'PENDING']
            context_lines.append(f"Total Pending Count: {len(pending)}")
            for _, d in pending.head(5).iterrows():
                context_lines.append(f"DO#{d.get('DO_Number')} - {d.get('Warehouse_Name')} ({d.get('Date_Issued')})")

    return "\n".join(context_lines)

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer.
You are provided with a pre-calculated 'Local Context' block. Base your answers strictly on this block.
If transferring stock to a branch, draft this exact ERP command format: 
`SRTS: Move [Qty] units of SKU [SKU] from [Donor] to [Destination]`

Style: Crisp, analytical, use bullet points and bold text.
"""

# =====================================================
# UI INJECTION & MODAL LOGIC
# =====================================================
@st.dialog("🤖 Intelligence Copilot", width="large")
def render_copilot_modal():
    st.markdown("""
        <style>
        /* Dialog Background & Headers */
        div[data-testid="stDialog"] div[role="dialog"] { background-color: #0B0F19 !important; border: 1px solid #1E293B !important; border-radius: 16px !important; }
        div[data-testid="stDialog"] header { background-color: #0B0F19 !important; }
        div[data-testid="stDialog"] h2, div[data-testid="stDialog"] [data-testid="stHeadingWithActionElements"] * { color: #38BDF8 !important; font-weight: 800 !important; }
        
        /* Quick Query Buttons */
        div[data-testid="stDialog"] div[data-testid="stButton"] button { background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid #334155 !important; font-weight: 600 !important; border-radius: 8px !important; transition: all 0.3s ease !important; }
        div[data-testid="stDialog"] div[data-testid="stButton"] button:hover { background-color: #38BDF8 !important; color: #020617 !important; border-color: #38BDF8 !important; }
        div[data-testid="stDialog"] div[data-testid="stButton"] button p { color: inherit !important; }
        
        /* Chat History Bubbles */
        div[data-testid="stChatMessage"] { background-color: #111827 !important; border: 1px solid #1E293B !important; border-radius: 12px !important; margin-bottom: 12px !important; padding: 14px !important; }
        div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] li, div[data-testid="stChatMessage"] span { color: #F8FAFC !important; font-size: 14px !important; line-height: 1.6 !important; }
        div[data-testid="stChatMessage"] strong { color: #38BDF8 !important; }
        
        /* Chat Input Field (Fixed White-on-White Issue) */
        div[data-testid="stChatInput"] { background-color: #0F172A !important; border: 1px solid #334155 !important; border-radius: 12px !important; }
        div[data-testid="stChatInput"] textarea { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; background-color: transparent !important; caret-color: #38BDF8 !important; }
        div[data-testid="stChatInput"] textarea::placeholder { color: #64748B !important; -webkit-text-fill-color: #64748B !important; }
        div[data-testid="stChatInput"] button { color: #38BDF8 !important; }
        </style>
    """, unsafe_allow_html=True)

    col_hdr, col_clear = st.columns([3, 1])
    with col_hdr:
        st.caption("⚡ Groq Engine: Ultra-Fast Data Processing")
    with col_clear:
        if st.button("🗑️ Reset & Sync", use_container_width=True):
            st.session_state.copilot_history = []
            get_or_fetch_stock_data(force_reload=True)
            get_or_fetch_do_ledger(force_reload=True)
            st.rerun()

    c1, c2, c3 = st.columns(3)
    quick_query = None
    if c1.button("🚨 Reorder in 1 Week", use_container_width=True): quick_query = "Which items do we need to reorder within 1 week?"
    if c2.button("📦 Pending DO Status", use_container_width=True): quick_query = "Summarize our current pending Delivery Orders."
    if c3.button("🔄 DIP Best Movers", use_container_width=True): quick_query = "Which is the best moving item in DIP warehouse?"

    if "copilot_history" not in st.session_state: st.session_state.copilot_history = []

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
            
            with st.spinner("Extracting local telemetry..."):
                local_context = build_live_context(query_to_process)
                final_prompt = f"LOCAL CONTEXT:\n{local_context}\n\nUSER QUESTION:\n{query_to_process}"
                
                # 100% Bulletproof Dynamic Model Selection
                active_models = [m.id for m in client.models.list().data]
                target_model = None
                
                # Try preferred models first
                for preferred in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                    if preferred in active_models:
                        target_model = preferred
                        break
                
                # Ultimate Fail-Safe: If preferred are offline, pick the very first Llama model running on Groq's servers
                if not target_model:
                    llama_models = [m for m in active_models if "llama" in m.lower()]
                    target_model = llama_models[0] if llama_models else active_models[0]
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": final_prompt}
                    ],
                    model=target_model,
                    temperature=0.1,
                )
                
                answer = chat_completion.choices[0].message.content

        except Exception as err:
            answer = f"⚠️ **System Error:** {err}"

        st.session_state.copilot_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
            st.rerun()


def inject_floating_copilot():
    # Premium Expressive Corporate UI with Glassmorphism
    st.markdown("""
        <style>
        .st-key-floating_copilot_btn { 
            position: fixed !important; 
            bottom: 85px !important; /* Elevated above the Manage App logo */
            right: 30px !important; 
            z-index: 2147483647 !important; /* Maximum z-index */
            width: auto !important; 
        }
        .st-key-floating_copilot_btn > button { 
            background: rgba(15, 23, 42, 0.85) !important; 
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            color: #E0F2FE !important; 
            font-family: 'Inter', sans-serif !important;
            font-size: 15px !important; 
            font-weight: 600 !important; 
            letter-spacing: 0.5px !important;
            border-radius: 50px !important; 
            padding: 14px 28px !important; 
            border: 1px solid rgba(56, 189, 248, 0.4) !important; 
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.2), inset 0 0 20px rgba(56, 189, 248, 0.1) !important; 
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important; 
            animation: premiumPulse 3.5s infinite alternate !important;
        }
        .st-key-floating_copilot_btn > button:hover { 
            transform: translateY(-6px) scale(1.04) !important; 
            background: rgba(15, 23, 42, 0.98) !important; 
            border: 1px solid rgba(56, 189, 248, 0.9) !important;
            box-shadow: 0 12px 30px rgba(56, 189, 248, 0.4), 0 0 20px rgba(56, 189, 248, 0.3) !important; 
            color: #FFFFFF !important; 
        }
        
        @keyframes premiumPulse {
            0% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.2), inset 0 0 20px rgba(56, 189, 248, 0.1); }
            100% { box-shadow: 0 0 25px rgba(56, 189, 248, 0.5), inset 0 0 25px rgba(56, 189, 248, 0.2); }
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("✨ Ask Copilot", key="floating_copilot_btn"):
        render_copilot_modal()
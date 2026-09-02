import json
import re
import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

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
            
            # Clean numeric columns across the entire inventory matching dashboard standards
            num_cols = [
                "Current_Stock", "Stock_Sharjah", "Stock_Al_Quoz", "Stock_DIP", "Stock_Abu_Dhabi",
                "Avg_Daily_Sales", "Baseline_Velocity", "Consistency_Score", "Total_Lifetime_Sales",
                "Velocity_Al_Quoz", "Velocity_Sharjah", "Velocity_DIP", "Velocity_Abu_Dhabi"
            ]
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
                else:
                    df[c] = 0.0
            
            df["Days_of_Coverage"] = df.apply(
                lambda r: 999.0 if r["Baseline_Velocity"] <= 0 else round(r["Current_Stock"] / r["Baseline_Velocity"], 1), axis=1
            )
            
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
# EXACT DASHBOARD REPLICATION FUNCTIONS
# =====================================================
WAREHOUSE_MAPPINGS = [
    {"stock_col": "Stock_Al_Quoz", "vel_col": "Velocity_Al_Quoz", "label": "Al Quoz"},
    {"stock_col": "Stock_Sharjah", "vel_col": "Velocity_Sharjah", "label": "Sharjah"},
    {"stock_col": "Stock_DIP", "vel_col": "Velocity_DIP", "label": "DIP"},
    {"stock_col": "Stock_Abu_Dhabi", "vel_col": "Velocity_Abu_Dhabi", "label": "Abu Dhabi"}
]

def calculate_dashboard_transfer_routes(df, source_filter=None, dest_filter=None, sku_filter=None):
    """
    Executes the exact DOI Balancing Engine logic from Stock_Transfer.py:
    - Target Stock = Total Stock * (Branch Velocity / Total Net Velocity)
    - Deficit: Net Need > 1.0 and Runway < 12.0 days
    - Surplus: Net Need < -1.0 or (Velocity == 0 and Stock >= 1)
    - Safe Donor Limit: Stock - (10.0 * Velocity) if active, else 100% of stock
    """
    if df.empty:
        return []

    routes = []
    
    for _, row in df.iterrows():
        sku = str(row.get("Item_Code", "")).strip()
        name = str(row.get("Item_Name", "")).strip()
        total_system_stock = float(row.get("Current_Stock", 0.0))
        
        if sku_filter and (sku_filter.upper() not in sku.upper() and sku_filter.upper() not in name.upper()):
            continue
            
        total_net_vel = sum(float(row.get(w["vel_col"], 0.0)) for w in WAREHOUSE_MAPPINGS)
        if total_net_vel <= 0 or total_system_stock <= 0:
            continue

        branch_needs = []
        for w in WAREHOUSE_MAPPINGS:
            b_vel = float(row.get(w["vel_col"], 0.0))
            b_stock = float(row.get(w["stock_col"], 0.0))
            
            demand_share = b_vel / total_net_vel if total_net_vel > 0 else 0.25
            target_stock = total_system_stock * demand_share
            net_need = target_stock - b_stock
            b_runway = (b_stock / b_vel) if b_vel > 0 else 999.0
            
            branch_needs.append({
                "label": w["label"],
                "stock": b_stock,
                "vel": b_vel,
                "runway": b_runway,
                "net_need": net_need
            })

        deficits = [b for b in branch_needs if b["net_need"] > 1.0 and b["runway"] < 12.0]
        surpluses = [b for b in branch_needs if b["net_need"] < -1.0 or (b["vel"] == 0 and b["stock"] >= 1)]

        for dest in deficits:
            for src in surpluses:
                if dest["label"] == src["label"]:
                    continue
                
                # Apply source/destination filters if requested
                if source_filter and source_filter.lower() not in src["label"].lower():
                    continue
                if dest_filter and dest_filter.lower() not in dest["label"].lower():
                    continue

                if src["vel"] > 0:
                    src_safe_donor_limit = max(0, int(src["stock"] - (10.0 * src["vel"])))
                    donor_type = f"Surplus (~{src['runway']:.1f}d runway)"
                else:
                    src_safe_donor_limit = int(src["stock"])
                    donor_type = "IDLE (0 local sales)"

                optimal_transfer = min(int(dest["net_need"]), src_safe_donor_limit)
                
                if optimal_transfer >= 1:
                    routes.append({
                        "SKU": sku,
                        "Name": name,
                        "Destination": dest["label"],
                        "Dest_Stock": int(dest["stock"]),
                        "Dest_Burn": round(dest["vel"], 2),
                        "Dest_Runway": round(dest["runway"], 1),
                        "Donor": src["label"],
                        "Donor_Stock": int(src["stock"]),
                        "Donor_Type": donor_type,
                        "Transfer_Qty": int(optimal_transfer),
                        "ERP_Command": f"SRTS: Move {int(optimal_transfer)} units of SKU {sku} from {src['label']} to {dest['label']}"
                    })
                    break  # Match one donor per deficit branch per SKU
    return routes

# =====================================================
# TELEMETRY PAYLOAD BUILDER (DETERMINISTIC DATA INJECTION)
# =====================================================
def build_live_context(query: str) -> str:
    """Pre-calculates exact figures using the dashboard's internal code logic."""
    df_s = get_or_fetch_stock_data()
    df_do = get_or_fetch_do_ledger()
    if df_s.empty:
        return "System Notice: Live inventory dataset is unreachable."

    query_upper = query.upper()
    sections = []

    # Detect Route Filters in user's prompt (e.g., "Sharjah to Abu Dhabi")
    src_branch = None
    dest_branch = None
    for wh in ["Sharjah", "Abu Dhabi", "Al Quoz", "DIP"]:
        if f"FROM {wh.upper()}" in query_upper:
            src_branch = wh
        if f"TO {wh.upper()}" in query_upper:
            dest_branch = wh

    # 1. RUN TRANSFER ENGINE (Exact Stock_Transfer.py match)
    all_transfer_routes = calculate_dashboard_transfer_routes(df_s, source_filter=src_branch, dest_filter=dest_branch)
    
    if all_transfer_routes:
        t_lines = []
        for r in all_transfer_routes[:15]:
            t_lines.append(
                f"- SKU {r['SKU']} ({r['Name']}): Move {r['Transfer_Qty']} units from {r['Donor']} ({r['Donor_Stock']} on hand, {r['Donor_Type']}) "
                f"to {r['Destination']} (Has {r['Dest_Stock']} units, Runway: {r['Dest_Runway']}d, Burn: {r['Dest_Burn']}/d). "
                f"Command: `{r['ERP_Command']}`"
            )
        sections.append(f"=== DASHBOARD VERIFIED TRANSFER ROUTES (Source: {src_branch or 'Any'}, Dest: {dest_branch or 'Any'}) ===\n" + "\n".join(t_lines))
    else:
        sections.append(f"=== DASHBOARD VERIFIED TRANSFER ROUTES ===\nNo transfer deficits detected matching routes (Source: {src_branch or 'Any'} -> Dest: {dest_branch or 'Any'}).")

    # 2. RUN FAST-MOVERS / BEST-MOVERS (Ranked by Baseline Velocity)
    top_movers_df = df_s.sort_values(by='Baseline_Velocity', ascending=False).head(10)
    mover_lines = []
    for rank, (_, r) in enumerate(top_movers_df.iterrows(), 1):
        mover_lines.append(
            f"{rank}. SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | "
            f"Daily Run-Rate: {r['Baseline_Velocity']:.2f} units/day | Total Stock: {int(r['Current_Stock'])} | "
            f"Runway: {r['Days_of_Coverage']:.1f} days [SHJ: {int(r.get('Stock_Sharjah', 0))}, AQ: {int(r.get('Stock_Al_Quoz', 0))}, "
            f"DIP: {int(r.get('Stock_DIP', 0))}, AD: {int(r.get('Stock_Abu_Dhabi', 0))}]"
        )
    sections.append("=== VERIFIED TOP 10 BEST-MOVING ITEMS (NETWORK-WIDE) ===\n" + "\n".join(mover_lines))

    # 3. RUN CRITICAL REORDER CANDIDATES (< 7 Days Coverage matching Sales_&_Stock_Tracking.py)
    reorders_df = df_s[
        (df_s['Baseline_Velocity'] > 0.05) & 
        (df_s['Days_of_Coverage'] <= 7.0)
    ].sort_values(by='Days_of_Coverage').head(12)
    
    reorder_lines = []
    for _, r in reorders_df.iterrows():
        reorder_lines.append(
            f"- SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | Stock: {int(r['Current_Stock'])} units | "
            f"Burn Rate: {r['Baseline_Velocity']:.2f}/day | Runway: {r['Days_of_Coverage']:.1f} days | Class: {r.get('ABC_Category', 'N/A')}"
        )
    if reorder_lines:
        sections.append("=== VERIFIED HIGH-RISK REORDER CANDIDATES (RUNWAY <= 7 DAYS) ===\n" + "\n".join(reorder_lines))

    # 4. TARGETED SKU LOOKUP (If user asked about specific product)
    sku_matches = df_s[
        df_s['Item_Code'].astype(str).str.upper().apply(lambda x: x in query_upper if x else False) |
        df_s['Item_Name'].astype(str).str.upper().apply(lambda x: any(word in query_upper for word in str(x).split() if len(word) > 3))
    ]
    if not sku_matches.empty:
        sku_lines = []
        for _, r in sku_matches.head(4).iterrows():
            sku_lines.append(
                f"- SKU: {r.get('Item_Code')} | Name: {r.get('Item_Name')} | Category: {r.get('Product_Category')} | "
                f"Total Stock: {int(r['Current_Stock'])} | Run-Rate: {r['Baseline_Velocity']:.2f}/day | Runway: {r['Days_of_Coverage']:.1f}d | "
                f"Locations: [SHJ: {int(r.get('Stock_Sharjah', 0))}, AQ: {int(r.get('Stock_Al_Quoz', 0))}, DIP: {int(r.get('Stock_DIP', 0))}, AD: {int(r.get('Stock_Abu_Dhabi', 0))}]"
            )
        sections.append("=== SPECIFIC SKU TELEMETRY ===\n" + "\n".join(sku_lines))

    # 5. DISPATCH QUEUE OVERVIEW
    if not df_do.empty and "Status" in df_do.columns:
        pending_dos = df_do[df_do['Status'].astype(str).str.upper() == 'PENDING']
        sections.append(f"=== DISPATCH QUEUE ===\nTotal Pending DO Backlog Count: {len(pending_dos)} orders.")

    return "\n\n".join(sections)

# =====================================================
# AGENT SYSTEM INSTRUCTIONS
# =====================================================
SYSTEM_PROMPT = """
You are the Chief Inventory Intelligence Officer & Senior Logistics Analyst for Sabin Plastic.
You communicate exact, verified calculations from our enterprise warehouse tracking system.

Directives:
1. Grounding: Answer strictly using facts in the 'LOCAL CONTEXT' section. The numbers in the context were generated by our production transfer and demand equations. Never recompute or alter these numbers.
2. Inter-Branch Stock Transfers:
   - Present recommendations in a clean Markdown Table with columns: `SKU`, `Item Description`, `Donor Warehouse`, `Destination Warehouse`, `Suggested Transfer Qty`, and `Destination Runway (Days)`.
   - Provide the exact Focus ERP command formatted in a code block:
     `SRTS: Move [Qty] units of SKU [SKU] from [Donor Warehouse] to [Destination Warehouse]`
3. Reorders & Best Movers:
   - Present best-moving items or reorder recommendations using clean Markdown Tables with bold SKU codes and exact run-rates.
4. Output Rules:
   - Start directly with the answer in sentence 1.
   - Never output internal thinking tags, reasoning monologues, or greetings.
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

        /* 7. CHAT MESSAGE CARDS */
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
    if c1.button("🏆 Top 10 Best Moving Items", use_container_width=True): 
        quick_query = "Which are the top 10 best moving items across our warehouses?"
    if c2.button("🚨 High-Risk Reorders (<7d)", use_container_width=True): 
        quick_query = "Which items do we need to reorder within 7 days based on current burn rate?"
    if c3.button("🔄 Proportional Transfer Routes", use_container_width=True): 
        quick_query = "Check all warehouses and suggest immediate inter-branch stock transfers based on our DOI balancing engine."

    if "copilot_history" not in st.session_state: 
        st.session_state.copilot_history = []

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
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    ">
    ⚡ AI Inventory Intelligence • Real-Time Warehouse Analytics • Powered by Groq
    </div>
    """, unsafe_allow_html=True)

    user_input = st.chat_input("Ask about transfers, top movers, reorders, or specific SKUs...")
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
                
                # Strict Model Filter: Filter out any reasoning models to prevent <think> tags
                live_models = client.models.list().data
                non_reasoning_models = [
                    m.id for m in live_models 
                    if not any(k in m.id.lower() for k in ["deepseek", "r1", "distill", "qwq", "guard", "whisper", "vision"])
                ]
                
                target_model = None
                for pref in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
                    if pref in non_reasoning_models:
                        target_model = pref
                        break
                
                if not target_model:
                    target_model = non_reasoning_models[0] if non_reasoning_models else "llama-3.3-70b-versatile"

                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": final_prompt}
                    ],
                    model=target_model,
                    temperature=0.0,
                    max_tokens=2048
                )
                raw_response = chat_completion.choices[0].message.content

                # Multi-stage thought cleaner
                cleaned_answer = re.sub(r"<think>[\s\S]*?</think>", "", raw_response).strip()
                cleaned_answer = re.sub(r"<think>[\s\S]*$", "", cleaned_answer).strip()
                cleaned_answer = re.sub(r"^Here's a thinking process:[\s\S]*?(?=\n\n|\n[A-Z0-9#|])", "", cleaned_answer).strip()

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
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
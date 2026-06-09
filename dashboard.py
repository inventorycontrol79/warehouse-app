import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 1. Page Configuration Setup
st.set_page_config(
    page_title="SABIN // Logistics Intelligence", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Complete Custom UI Injector (Neon Glow Cyber Grid Architecture)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    .stApp { 
        background-color: #030712;
        background-image: 
            linear-gradient(rgba(6, 182, 212, 0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.04) 1px, transparent 1px),
            radial-gradient(circle at 50% 10%, #081d33 0%, #030712 70%);
        background-size: 40px 40px, 40px 40px, 100% 100%;
        color: #f8fafc; 
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .brand-frame {
        text-align: center;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(12px);
        padding: 20px 40px;
        border-radius: 16px;
        border: 2px solid #00f2fe;
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.25), inset 0 0 15px rgba(0, 242, 254, 0.1);
        margin-bottom: 35px;
    }
    .brand-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 50px;
        font-weight: 800;
        letter-spacing: 6px;
        background: linear-gradient(180deg, #ffffff 0%, #a5f3fc 50%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(0, 242, 254, 0.4);
        margin: 0;
        line-height: 1.1;
    }
    .brand-subtitle {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 4px;
        color: #94a3b8;
        margin-top: 8px;
        font-weight: 600;
    }

    .status-ribbon {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
        padding: 0 10px;
    }
    .section-headline {
        font-family: 'Orbitron', sans-serif;
        font-size: 14px;
        letter-spacing: 2px;
        color: #38bdf8;
        font-weight: 500;
    }
    .engine-badge {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #10b981;
        background: rgba(16, 185, 129, 0.08);
        padding: 6px 14px;
        border-radius: 6px;
        border: 1px solid rgba(16, 185, 129, 0.3);
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.15);
    }
    
    div[data-testid="stMetric"] { 
        background: rgba(10, 15, 30, 0.7) !important;
        backdrop-filter: blur(20px);
        padding: 20px !important; 
        border-radius: 12px !important; 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Neon Borders Setup for 5-Column Grid Layout */
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"] { border: 1px solid rgba(6, 182, 212, 0.3) !important; }
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"]:hover { border-color: #06b6d4 !important; box-shadow: 0 0 20px rgba(6, 182, 212, 0.25); }
    
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"] { border: 1px solid rgba(245, 158, 11, 0.3) !important; }
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"]:hover { border-color: #f59e0b !important; box-shadow: 0 0 20px rgba(245, 158, 11, 0.25); }
    
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"] { border: 1px solid rgba(16, 185, 129, 0.3) !important; }
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"]:hover { border-color: #10b981 !important; box-shadow: 0 0 20px rgba(16, 185, 129, 0.25); }
    
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"] { border: 1px solid rgba(239, 68, 68, 0.3) !important; }
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"]:hover { border-color: #ef4444 !important; box-shadow: 0 0 20px rgba(239, 68, 68, 0.25); }

    div[data-testid="stCol"]:nth-of-type(5) div[data-testid="stMetric"] { border: 1px solid rgba(168, 85, 247, 0.3) !important; }
    div[data-testid="stCol"]:nth-of-type(5) div[data-testid="stMetric"]:hover { border-color: #a855f7 !important; box-shadow: 0 0 20px rgba(168, 85, 247, 0.25); }

    div[data-testid="stMetricValue"] { 
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 28px !important; 
        font-weight: 700 !important; 
        color: #ffffff !important;
    }
    div[data-testid="stMetricLabel"] { 
        color: #94a3b8 !important; 
        text-transform: uppercase !important; 
        letter-spacing: 2px !important; 
        font-size: 10px !important; 
        font-weight: 700 !important;
    }
    
    .stSidebar { 
        background-color: #02050a !important; 
        border-right: 1px solid rgba(6, 182, 212, 0.15) !important; 
    }
    
    .stSelectbox label, .stDateInput label { 
        color: #cbd5e1 !important; 
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stDataFrame { 
        background: rgba(10, 15, 30, 0.6) !important; 
        border-radius: 12px; 
        border: 1px solid rgba(56, 189, 248, 0.2);
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        padding: 10px;
    }
    
    div.stDownloadButton > button {
        background: linear-gradient(135deg, rgba(245,158,11,0.15) 0%, rgba(245,158,11,0.05) 100%) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245,158,11,0.4) !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        font-size: 11px !important;
        padding: 12px 30px !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    div.stDownloadButton > button:hover {
        background: rgba(245,158,11,0.25) !important;
        border-color: #f59e0b !important;
        box-shadow: 0 0 20px rgba(245,158,11,0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Top-Bar Branding Deployment
st.markdown("""
<div class="brand-frame">
    <div class="brand-title">SABIN</div>
    <div class="brand-subtitle">Warehouse Master Portal // Logistics Intelligence</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="status-ribbon">
    <div class="section-headline">SABIN // WAREHOUSE COMMAND CENTER</div>
    <div class="engine-badge">● WHATSAPP AUTOMATION STANDBY</div>
</div>
""", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'

try:
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=['Location', 'Status', 'Date_Issued', 'Quantity', 'Last_4', 'DO_Number']).to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    # ------------------ SIDEBAR CONTROL CONFIGURATIONS ------------------
    st.sidebar.markdown("<h3 style='font-family:Orbitron; letter-spacing:1px; font-size:16px; margin-bottom:-10px; color:#38bdf8;'>CONTROL DESK</h3>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    st.sidebar.markdown("<p style='font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#94a3b8; font-weight:700; margin-bottom:5px;'>Import ERP Manifest</p>", unsafe_allow_html=True)
    uploaded_file = st.sidebar.file_uploader("Drop report file", type=['csv', 'xlsx'], label_visibility="collapsed")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                uploaded_df = pd.read_excel(uploaded_file)
            else:
                uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df.to_csv(CSV_FILE, index=False)
            st.sidebar.success("Manifest re-mapped.")
            df = pd.read_csv(CSV_FILE) 
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error handling manifest: {e}")

    # Location Filter
    LOCATION_COLUMN = 'Location' 
    if LOCATION_COLUMN in df.columns:
        df[LOCATION_COLUMN] = df[LOCATION_COLUMN].astype(str).str.strip()
        unique_locations = sorted(list(df[LOCATION_COLUMN].unique()))
        url_params = st.query_params
        if "warehouse" in url_params and url_params["warehouse"] in unique_locations and url_params.get("role") == "supervisor":
            target_warehouse = url_params["warehouse"]
            st.sidebar.info(f"📍 Locked: {target_warehouse}")
            df = df[df[LOCATION_COLUMN] == target_warehouse]
        else:
            master_options = ["All Terminals"] + unique_locations
            selected_location = st.sidebar.selectbox("Active Terminal Station", master_options)
            if selected_location != "All Terminals":
                df = df[df[LOCATION_COLUMN] == selected_location]

    # Status Filter
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
        status_options = ["All Metrics", "Pending Only"] + [f"{s} Only" for s in df[STATUS_COLUMN].unique() if s != 'Pending']
        selected_status = st.sidebar.selectbox("Filter Status Stream", status_options)
        if "Pending Only" in selected_status:
            df = df[df[STATUS_COLUMN] == 'Pending']
        elif "All Metrics" not in selected_status:
            df = df[df[STATUS_COLUMN] == selected_status.replace(" Only", "")]

    # Date Filter
    DATE_COLUMN = 'Date_Issued' 
    if DATE_COLUMN in df.columns:
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce').dt.date
        clean_dates = df[DATE_COLUMN].dropna()
        if not clean_dates.empty:
            start_date = st.sidebar.date_input("From Date", min(clean_dates))
            end_date = st.sidebar.date_input("To Date", max(clean_dates))
            filtered_df = df[(df[DATE_COLUMN] >= start_date) & (df[DATE_COLUMN] <= end_date)]
        else: filtered_df = df
    else: filtered_df = df

    # ------------------ DISPLAY LABELS ENGINE ------------------
    count_dispatched = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Dispatched']) if STATUS_COLUMN in filtered_df.columns else 0
    count_pending = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Pending']) if STATUS_COLUMN in filtered_df.columns else len(filtered_df)
    count_return = len(filtered_df[filtered_df[STATUS_COLUMN] == 'Return']) if STATUS_COLUMN in filtered_df.columns else 0
    total_volume = filtered_df['Quantity'].sum() if 'Quantity' in filtered_df.columns else 0

    # Option A: Balanced 5-Column Dashboard Lineup
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Total Load Profile", f"{len(filtered_df):,}")
    with m2: st.metric("Pending Queue", f"{count_pending:,}")
    with m3: st.metric("Dispatched Volume", f"{count_dispatched:,}")
    with m4: st.metric("Return Logs", f"{count_return:,}")
    with m5: st.metric("Gross Units Moved", f"{total_volume:,}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-family:Orbitron; font-size:13px; letter-spacing:1px; color:#94a3b8; margin-bottom:12px;'>LIVE OPERATIONS PIPELINE</h4>", unsafe_allow_html=True)

    def style_premium_cells(val):
        clean_val = str(val).strip()
        if clean_val == 'Dispatched': return 'color: #10b981; font-weight: 700; background-color: rgba(16, 185, 129, 0.04);'
        elif clean_val == 'Return': return 'color: #ef4444; font-weight: 700; background-color: rgba(239, 68, 68, 0.04);'
        elif clean_val == 'Pending': return 'color: #f59e0b; font-weight: 700; background-color: rgba(245, 158, 11, 0.04);'
        return ''

    if len(filtered_df) > 0:
        if STATUS_COLUMN in filtered_df.columns:
            st.dataframe(filtered_df.style.map(style_premium_cells, subset=[STATUS_COLUMN]), use_container_width=True, height=450)
        else: st.dataframe(filtered_df, use_container_width=True, height=450)
    else: st.info("No logs match the requested configuration streams.")

    # ------------------ ADVANCED PRESTIGE EXCEL GENERATOR ------------------
    if not filtered_df.empty:
        excel_buffer = io.BytesIO()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Manifest Log"
        ws.views.sheetView[0].showGridLines = True
        
        font_family = "Segoe UI"
        
        title_font = Font(name=font_family, size=15, bold=True, color="0F172A")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
        card_label_font = Font(name=font_family, size=9, bold=True, color="64748B")
        card_val_font = Font(name=font_family, size=14, bold=True, color="0F172A")
        card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        
        thin_side = Side(style='thin', color='E2E8F0')
        border_all = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        
        status_styles = {
            "Pending": {"fill": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"), "font": Font(name=font_family, size=10, bold=True, color="B45309")},
            "Dispatched": {"fill": PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"), "font": Font(name=font_family, size=10, bold=True, color="047857")},
            "Return": {"fill": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"), "font": Font(name=font_family, size=10, bold=True, color="B91C1C")}
        }

        # Title Row
        ws.merge_cells("A2:F2")
        ws["A2"] = "SABIN // EXECUTIVE LOGISTICS MANIFEST"
        ws["A2"].font = title_font
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
        
        # Recover True Status Column Letter Dynamically
        columns_mapping = list(filtered_df.columns)
        status_col_idx = 2  
        for idx, col_name in enumerate(columns_mapping, 1):
            if "status" in str(col_name).lower():
                status_col_idx = idx
                break
        
        status_letter = get_column_letter(status_col_idx)
        total_rows_data = len(filtered_df)
        last_row_idx = 8 + total_rows_data
        
        # Option A: Extended Formula KPI Header Lineup inside the Workbook
        cards_setup = [
            ("TOTAL LOAD PROFILE", f"=COUNTA(A9:A{last_row_idx})", "A", "B"),
            ("PENDING QUEUE", f'=COUNTIF({status_letter}9:{status_letter}{last_row_idx}, "Pending")', "C", "D"),
            ("DISPATCHED VOLUME", f'=COUNTIF({status_letter}9:{status_letter}{last_row_idx}, "Dispatched")', "E", "F"),
            ("RETURN RECORDS", f'=COUNTIF({status_letter}9:{status_letter}{last_row_idx}, "Return")', "G", "H")
        ]
        
        for lbl, formula, c1, c2 in cards_setup:
            ws.merge_cells(f"{c1}4:{c2}4")
            ws.merge_cells(f"{c1}5:{c2}5")
            ws[f"{c1}4"] = lbl
            ws[f"{c1}4"].font = card_label_font
            ws[f"{c1}4"].fill = card_fill
            ws[f"{c2}4"].fill = card_fill
            ws[f"{c1}4"].alignment = Alignment(horizontal="center", vertical="center")
            
            ws[f"{c1}5"] = formula
            ws[f"{c1}5"].font = card_val_font
            ws[f"{c1}5"].fill = card_fill
            ws[f"{c2}5"].fill = card_fill
            ws[f"{c1}5"].alignment = Alignment(horizontal="center", vertical="center")
            
            for r in [4, 5]:
                ws[f"{c1}{r}"].border = border_all
                ws[f"{c2}{r}"].border = border_all

        # Headers Row Generation
        ws.row_dimensions[8].height = 26
        for col_idx, column_name in enumerate(columns_mapping, 1):
            cell = ws.cell(row=8, column=col_idx, value=str(column_name))
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border_all
            cell.alignment = Alignment(horizontal="center" if "status" in str(column_name).lower() else "left", vertical="center")

        # Inject Data Rows
        for r_idx, row_values in enumerate(filtered_df.itertuples(index=False), 9):
            ws.row_dimensions[r_idx].height = 22
            for c_idx, cell_value in enumerate(row_values, 1):
                col_name = columns_mapping[c_idx - 1]
                cell = ws.cell(row=r_idx, column=c_idx, value=cell_value)
                cell.font = Font(name=font_family, size=10, color="334155")
                cell.border = border_all
                
                if isinstance(cell_value, (int, float)):
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = '#,##0'
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

                if r_idx % 2 == 0:
                    cell.fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

                if "status" in str(col_name).lower():
                    status_str = str(cell_value).strip()
                    if status_str in status_styles:
                        cell.fill = status_styles[status_str]["fill"]
                        cell.font = status_styles[status_str]["font"]
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto-adjust column dimensions beautifully
        for col in ws.columns:
            vals = [str(c.value or '') for c in col if c.row >= 8]
            max_len = max(len(v) for v in vals) if vals else 10
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 5, 15)

        wb.save(excel_buffer)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="Download Executive Report ↓",
            data=excel_buffer.getvalue(),
            file_name=f"SABIN_Manifest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

except FileNotFoundError: st.error("🚨 Configuration Error: Missing core data source elements.")
except Exception as e: st.error(f"Pipeline loop error: {e}")
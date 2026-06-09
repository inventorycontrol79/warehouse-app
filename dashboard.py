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
    page_title="SABIN // Enterprise Command", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Premium Luxury Textured Architecture UI Injector
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700&family=Plus+Jakarta+Sans:wght@700;800&display=swap');
    
    /* Institutional Matte Satin Background with Micro-Carbon Weave Texture */
    .stApp { 
        background-color: #060911;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(30, 41, 59, 0.45) 0%, #060911 85%),
            linear-gradient(rgba(255, 255, 255, 0.008) 2px, transparent 2px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.008) 2px, transparent 2px);
        background-size: 100% 100%, 8px 8px, 8px 8px;
        color: #f1f5f9; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Monolithic Platinum Glass Brand Frame (Inspired by Luxury Automotive Design Language) */
    .brand-frame {
        position: relative;
        text-align: left;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        backdrop-filter: blur(40px);
        -webkit-backdrop-filter: blur(40px);
        padding: 40px 50px;
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #f8fafc; /* Asymmetrical Platinum Architectural Detail */
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        margin-bottom: 35px;
        overflow: hidden;
    }
    .brand-frame::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, rgba(255,255,255,0.15), transparent);
    }
    .brand-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 42px;
        font-weight: 800;
        letter-spacing: 12px;
        text-transform: uppercase;
        background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.0;
    }
    .brand-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 5px;
        color: #64748b;
        margin-top: 12px;
        font-weight: 500;
    }

    /* Subdued Operations Ribbon */
    .status-ribbon {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        padding: 0 4px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 14px;
    }
    .section-headline {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        color: #94a3b8;
        font-weight: 700;
    }
    .engine-badge {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        color: #cbd5e1;
        background: rgba(255, 255, 255, 0.04);
        padding: 5px 16px;
        border-radius: 2px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-transform: uppercase;
    }
    
    /* Tailored Monolithic Telemetry Cards */
    div[data-testid="stMetric"] { 
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.25) 0%, rgba(15, 23, 42, 0.45) 100%) !important;
        backdrop-filter: blur(20px);
        padding: 24px 28px !important; 
        border-radius: 2px !important; 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    /* Sophisticated Low-Profile Highlight Interactivity */
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"] { border: 1px solid rgba(255, 255, 255, 0.05) !important; border-top: 2px solid #64748b !important; }
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"]:hover { background: rgba(255, 255, 255, 0.04) !important; border-top-color: #ffffff !important; }
    
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"] { border: 1px solid rgba(255, 255, 255, 0.05) !important; border-top: 2px solid #d97706 !important; }
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"]:hover { background: rgba(255, 255, 255, 0.04) !important; border-top-color: #f59e0b !important; }
    
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"] { border: 1px solid rgba(255, 255, 255, 0.05) !important; border-top: 2px solid #059669 !important; }
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"]:hover { background: rgba(255, 255, 255, 0.04) !important; border-top-color: #10b981 !important; }
    
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"] { border: 1px solid rgba(255, 255, 255, 0.05) !important; border-top: 2px solid #dc2626 !important; }
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"]:hover { background: rgba(255, 255, 255, 0.04) !important; border-top-color: #ef4444 !important; }

    div[data-testid="stMetricValue"] { 
        font-family: 'Inter', sans-serif;
        font-size: 38px !important; 
        font-weight: 300 !important; /* Elegant architectural light-weight number look */
        color: #ffffff !important;
        letter-spacing: -1.5px;
        margin-top: 4px;
    }
    div[data-testid="stMetricLabel"] { 
        color: #64748b !important; 
        text-transform: uppercase !important; 
        letter-spacing: 2px !important; 
        font-size: 10px !important; 
        font-weight: 600 !important;
    }
    
    /* Sidebar Minimal Styling */
    .stSidebar { 
        background-color: #03050a !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.04) !important; 
    }
    
    .stSelectbox label, .stDateInput label { 
        color: #64748b !important; 
        font-size: 10px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Clean Industrial Data Grid Overrides */
    .stDataFrame { 
        background: rgba(15, 23, 42, 0.2) !important; 
        border-radius: 4px; 
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 4px;
    }
    
    /* Tailored Industrial Platinum Action Button */
    div.stDownloadButton > button {
        background: transparent !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        font-weight: 500 !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        font-size: 10px !important;
        padding: 12px 28px !important;
        border-radius: 2px !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div.stDownloadButton > button:hover {
        background: #ffffff !important;
        color: #060911 !important;
        border-color: #ffffff !important;
        box-shadow: 0 15px 30px rgba(255,255,255,0.08) !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Top-Bar Branding Deployment
st.markdown("""
<div class="brand-frame">
    <div class="brand-title">SABIN</div>
    <div class="brand-subtitle">Logistics Intelligence & Corporate Operations</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="status-ribbon">
    <div class="section-headline">Live Management Pipeline</div>
    <div class="engine-badge">System Secure // Standby</div>
</div>
""", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'

try:
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=['Location', 'Status', 'Date_Issued', 'Last_4', 'DO_Number']).to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    # ------------------ SIDEBAR CONTROL CONFIGURATIONS ------------------
    st.sidebar.markdown("<p style='font-family:Inter; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:#ffffff; margin-bottom:20px;'>Console Desk</p>", unsafe_allow_html=True)

    st.sidebar.markdown("<p style='font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#475569; font-weight:600; margin-bottom:5px;'>Import ERP Manifest</p>", unsafe_allow_html=True)
    uploaded_file = st.sidebar.file_uploader("Drop report file", type=['csv', 'xlsx'], label_visibility="collapsed")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                uploaded_df = pd.read_excel(uploaded_file)
            else:
                uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df.to_csv(CSV_FILE, index=False)
            st.sidebar.success("Source aligned.")
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
            st.sidebar.info(f"Station: {target_warehouse}")
            df = df[df[LOCATION_COLUMN] == target_warehouse]
        else:
            master_options = ["All Terminals"] + unique_locations
            selected_location = st.sidebar.selectbox("Terminal Station", master_options)
            if selected_location != "All Terminals":
                df = df[df[LOCATION_COLUMN] == selected_location]

    # Status Filter
    STATUS_COLUMN = 'Status' 
    if STATUS_COLUMN in df.columns:
        df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
        status_options = ["All Metrics", "Pending Only"] + [f"{s} Only" for s in df[STATUS_COLUMN].unique() if s != 'Pending']
        selected_status = st.sidebar.selectbox("Status Stream", status_options)
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

    # Pristine 4-Column Balanced Lineup
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Load Profile", f"{len(filtered_df):,}")
    with m2: st.metric("Pending Queue", f"{count_pending:,}")
    with m3: st.metric("Dispatched Volume", f"{count_dispatched:,}")
    with m4: st.metric("Return Records", f"{count_return:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    def style_premium_cells(val):
        clean_val = str(val).strip()
        if clean_val == 'Dispatched': return 'color: #10b981; font-weight: 600; background-color: rgba(16, 185, 129, 0.03);'
        elif clean_val == 'Return': return 'color: #f43f5e; font-weight: 600; background-color: rgba(244, 63, 94, 0.03);'
        elif clean_val == 'Pending': return 'color: #f59e0b; font-weight: 600; background-color: rgba(245, 158, 11, 0.03);'
        return ''

    if len(filtered_df) > 0:
        if STATUS_COLUMN in filtered_df.columns:
            st.dataframe(filtered_df.style.map(style_premium_cells, subset=[STATUS_COLUMN]), use_container_width=True, height=500)
        else: st.dataframe(filtered_df, use_container_width=True, height=500)
    else: st.info("No records match your selected configuration filters.")

    # ------------------ ADVANCED PRESTIGE EXCEL GENERATOR ------------------
    if not filtered_df.empty:
        excel_buffer = io.BytesIO()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Executive Manifest"
        ws.views.sheetView[0].showGridLines = True
        
        font_family = "Segoe UI"
        
        title_font = Font(name=font_family, size=14, bold=True, color="0F172A")
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

        # Title Row Banner
        ws.merge_cells("A2:F2")
        ws["A2"] = "SABIN // EXECUTIVE LOGISTICS CONTROL MANIFEST"
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
        
        # Corporate 4-Card Balanced Head KPI Lineup
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

        # Inject Data Rows Matrix
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
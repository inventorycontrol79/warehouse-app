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
    page_title="SABIN // Operations Command", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. Premium Executive Obsidian Theme UI Injector
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@500;700;800&display=swap');
    
    /* Global Background and Typography Reset */
    .stApp { 
        background-color: #090d16;
        background-image: 
            radial-gradient(circle at 50% 0%, #1e293b 0%, #090d16 75%);
        color: #f1f5f9; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Brand Frame Title Block */
    .brand-frame {
        text-align: left;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
        backdrop-filter: blur(20px);
        padding: 30px 40px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
        margin-bottom: 30px;
    }
    .brand-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
        margin: 0;
        line-height: 1.1;
    }
    .brand-subtitle {
        font-size: 13px;
        letter-spacing: 0.5px;
        color: #94a3b8;
        margin-top: 6px;
        font-weight: 400;
    }

    /* Operations Ribbon */
    .status-ribbon {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 25px;
        padding: 0 4px;
    }
    .section-headline {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 16px;
        color: #ffffff;
        font-weight: 700;
    }
    .engine-badge {
        font-size: 11px;
        font-weight: 600;
        color: #10b981;
        background: rgba(16, 185, 129, 0.06);
        padding: 6px 14px;
        border-radius: 100px;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    /* Institutional Metric Blocks */
    div[data-testid="stMetric"] { 
        background: rgba(15, 23, 42, 0.45) !important;
        backdrop-filter: blur(20px);
        padding: 22px !important; 
        border-radius: 10px !important; 
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        transition: all 0.25s ease-in-out;
    }
    
    /* Clean Corporate Accent Borders */
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"] { border: 1px solid rgba(148, 163, 184, 0.15) !important; }
    div[data-testid="stCol"]:nth-of-type(1) div[data-testid="stMetric"]:hover { border-color: #64748b !important; background: rgba(15, 23, 42, 0.6) !important; }
    
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"] { border: 1px solid rgba(245, 158, 11, 0.15) !important; }
    div[data-testid="stCol"]:nth-of-type(2) div[data-testid="stMetric"]:hover { border-color: #f59e0b !important; box-shadow: 0 0 15px rgba(245, 158, 11, 0.1); }
    
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"] { border: 1px solid rgba(16, 185, 129, 0.15) !important; }
    div[data-testid="stCol"]:nth-of-type(3) div[data-testid="stMetric"]:hover { border-color: #10b981 !important; box-shadow: 0 0 15px rgba(16, 185, 129, 0.1); }
    
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"] { border: 1px solid rgba(239, 68, 68, 0.15) !important; }
    div[data-testid="stCol"]:nth-of-type(4) div[data-testid="stMetric"]:hover { border-color: #ef4444 !important; box-shadow: 0 0 15px rgba(239, 68, 68, 0.1); }

    div[data-testid="stMetricValue"] { 
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 34px !important; 
        font-weight: 700 !important; 
        color: #ffffff !important;
        letter-spacing: -1px;
    }
    div[data-testid="stMetricLabel"] { 
        color: #94a3b8 !important; 
        text-transform: uppercase !important; 
        letter-spacing: 1px !important; 
        font-size: 11px !important; 
        font-weight: 600 !important;
    }
    
    /* Sidebar Luxury Restyling */
    .stSidebar { 
        background-color: #05070c !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important; 
    }
    
    .stSelectbox label, .stDateInput label { 
        color: #94a3b8 !important; 
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    /* Modern Data Grid Base Frame */
    .stDataFrame { 
        background: rgba(15, 23, 42, 0.3) !important; 
        border-radius: 10px; 
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 6px;
    }
    
    /* Corporate Premium Action Button */
    div.stDownloadButton > button {
        background: #ffffff !important;
        color: #090d16 !important;
        border: 1px solid #ffffff !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px !important;
        font-size: 12px !important;
        padding: 10px 24px !important;
        border-radius: 6px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div.stDownloadButton > button:hover {
        background: #e2e8f0 !important;
        border-color: #e2e8f0 !important;
        box-shadow: 0 4px 20px rgba(255,255,255,0.15) !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Top-Bar Branding Deployment
st.markdown("""
<div class="brand-frame">
    <div class="brand-title">SABIN</div>
    <div class="brand-subtitle">Enterprise Logistics Control Center</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="status-ribbon">
    <div class="section-headline">Live Control Stream</div>
    <div class="engine-badge">● AUTOMATION STANDBY</div>
</div>
""", unsafe_allow_html=True)

CSV_FILE = 'inventory.csv'

try:
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=['Location', 'Status', 'Date_Issued', 'Last_4', 'DO_Number']).to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    # ------------------ SIDEBAR CONTROL CONFIGURATIONS ------------------
    st.sidebar.markdown("<p style='font-family:Inter; font-size:14px; font-weight:600; color:#ffffff; margin-bottom:15px;'>Operations Console</p>", unsafe_allow_html=True)

    st.sidebar.markdown("<p style='font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#64748b; font-weight:600; margin-bottom:5px;'>Import ERP Manifest</p>", unsafe_allow_html=True)
    uploaded_file = st.sidebar.file_uploader("Drop report file", type=['csv', 'xlsx'], label_visibility="collapsed")
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                uploaded_df = pd.read_excel(uploaded_file)
            else:
                uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df.to_csv(CSV_FILE, index=False)
            st.sidebar.success("Manifest synced successfully.")
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
            st.sidebar.info(f"Locked Terminal: {target_warehouse}")
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

    # Clean 4-Column Balanced Lineup (Removed Gross Volume Column)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Load Profile", f"{len(filtered_df):,}")
    with m2: st.metric("Pending Queue", f"{count_pending:,}")
    with m3: st.metric("Dispatched Volume", f"{count_dispatched:,}")
    with m4: st.metric("Return Records", f"{count_return:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    def style_premium_cells(val):
        clean_val = str(val).strip()
        if clean_val == 'Dispatched': return 'color: #10b981; font-weight: 600; background-color: rgba(16, 185, 129, 0.05);'
        elif clean_val == 'Return': return 'color: #f43f5e; font-weight: 600; background-color: rgba(244, 63, 94, 0.05);'
        elif clean_val == 'Pending': return 'color: #f59e0b; font-weight: 600; background-color: rgba(245, 158, 11, 0.05);'
        return ''

    if len(filtered_df) > 0:
        if STATUS_COLUMN in filtered_df.columns:
            st.dataframe(filtered_df.style.map(style_premium_cells, subset=[STATUS_COLUMN]), use_container_width=True, height=480)
        else: st.dataframe(filtered_df, use_container_width=True, height=480)
    else: st.info("No records found matching selected logs criteria.")

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
# Premium High-Contrast Dark Theme CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=300;400;600;800&display=swap');
    
    /* Main App Background */
    .stApp { background-color: #0B0F19; color: #E2E8F0; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* 🚨 NEW: Force Sidebar to Match Dark Theme */
    [data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    [data-testid="stSidebar"] label { color: #94A3B8 !important; }
    
    /* 🚨 NEW: Style the File Uploader & Expander to look premium in dark mode */
    [data-testid="stExpander"] { background-color: #111827 !important; border: 1px solid #1E293B !important; border-radius: 8px; }
    [data-testid="stExpander"] summary { color: #F8FAFC !important; }
    [data-testid="stFileUploader"] section { background-color: #111827 !important; border: 1px dashed #38BDF8 !important; }
    
    /* Existing Typography and Cards */
    h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] p { color: #F8FAFC !important; }
    label, .stWidgetLabel p { color: #94A3B8 !important; font-weight: 600 !important; }
    .premium-header { border-bottom: 1px solid #1E293B; padding-bottom: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .sabin-logo { font-size: 32px; font-weight: 800; letter-spacing: 4px; color: #F8FAFC !important; margin: 0; line-height: 1.2; }
    .sabin-logo span { color: #0EA5E9 !important; }
    .sabin-sub { font-size: 11px; font-weight: 600; letter-spacing: 3px; color: #94A3B8 !important; text-transform: uppercase; margin-top: 4px; }
    .card-box { background-color: #111827; border: 1px solid #1E293B; border-radius: 8px; padding: 22px; margin-bottom: 20px; }
    .advice-card { background-color: #151F32; border-left: 4px solid #38BDF8; border-radius: 6px; padding: 16px; margin-bottom: 12px; border-top: 1px solid #1E293B; border-right: 1px solid #1E293B; border-bottom: 1px solid #1E293B; }
    .critical-badge { color: #F87171 !important; font-weight: 800; background-color: rgba(239, 68, 68, 0.15); padding: 4px 8px; border-radius: 4px; }
    .surplus-badge { color: #34D399 !important; font-weight: 800; background-color: rgba(52, 211, 153, 0.15); padding: 4px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)
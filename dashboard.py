import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Page Configuration & Custom CSS Styling for a Visually Catchy Theme
st.set_page_config(page_title="Al Quoz & Abu Dhabi Warehouse Logistics", layout="wide")

# Custom CSS injected for a dark, premium logistics theme (Midnight Blue & Neon accents)
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #ecf0f1;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00ffcc !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #a0aec0 !important;
    }
    .css-1d391kg {
        background-color: #1a202c;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Warehouse Inventory & Logistics Portal")
st.markdown("---")

# 2. Load Data Using Relative Cloud Path
try:
    # Read the data
    df = pd.read_csv('inventory.csv')
    
    # Clean/Convert Date Column safely (Change 'Date' to your actual column name if different)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.date
    else:
        # Fallback if no date column exists just to keep the app functional
        df['Date'] = datetime.today().date()

    # 3. Sidebar Filtering Logic
    st.sidebar.header("🎯 Filter Control Center")
    
    min_date = min(df['Date'])
    max_date = max(df['Date'])
    
    # Date Pickers
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    
    # Apply the Date Filter
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    # 4. Visually Catchy Metrics / KPI Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tracked Items", len(filtered_df))
    with col2:
        # Assumes you have a 'Quantity' or 'Stock' column
        total_stock = filtered_df['Quantity'].sum() if 'Quantity' in df.columns else "N/A"
        st.metric("Total Stock Level", total_stock)
    with col3:
        # Assumes you have a 'Location' column
        locations = filtered_df['Location'].nunique() if 'Location' in df.columns else "Active"
        st.metric("Active Warehouses", locations)

    st.markdown("### 📊 Live Stock Breakdown")
    
    # 5. Visual Charting (Interactive Plotly Chart)
    # Adjust x and y parameters based on your inventory.csv columns (e.g., 'Item', 'Quantity')
    if 'Quantity' in filtered_df.columns:
        x_axis = 'Item' if 'Item' in filtered_df.columns else filtered_df.columns[0]
        fig = px.bar(
            filtered_df, 
            x=x_axis, 
            y='Quantity', 
            template="plotly_dark",
            color_discrete_sequence=["#00ffcc"]
        )
        st.plotly_chart(fig, use_container_width=True)

    # 6. Data Display Table
    st.markdown("### 📋 Filtered Manifest Record")
    st.dataframe(filtered_df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ Error: 'inventory.csv' missing from cloud repository folder. Please commit via GitHub Desktop.")
except Exception as e:
    st.error(f"An error occurred: {e}")
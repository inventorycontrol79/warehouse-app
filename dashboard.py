import streamlit as st
import pandas as pd
import plotly.express as px
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

st.set_page_config(page_title="Warehouse Inventory Dashboard", layout="wide")
st.title("Warehouse Inventory Dashboard")

# CRITICAL FIX: The cloud reads the file directly from the repository folder
try:
    df = pd.read_csv('inventory.csv')
    
    # Simple data preview to make sure it loads
    st.success("Data loaded successfully from the cloud storage!")
    st.dataframe(df)
    
    # Your visualization code goes here (Plotly charts, metrics, etc.)
    # Example:
    # fig = px.bar(df, x='Item Name', y='Quantity')
    # st.plotly_chart(fig)

except FileNotFoundError:
    st.error("Error: 'inventory.csv' was not found in the cloud repository folder. Please verify your GitHub upload.")
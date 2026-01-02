import streamlit as st
from utils import load_data, filter_data

st.set_page_config(page_title="WC Report", layout="wide")

st.title("🚰 WC Meter Progress")

df = load_data()
wc_df = filter_data(df, "WC")

col1, col2 = st.columns(2)
col1.metric("Total WC Installed", wc_df["Installed"].sum())
col2.metric("Pending WC", wc_df["Pending"].sum())

# WC specific charts only

import streamlit as st
from utils import load_data, filter_data

st.set_page_config(page_title="DT Report", layout="wide")

st.title("⚡ DT Meter Progress")

df = load_data()
dt_df = filter_data(df, "DT")

col1, col2 = st.columns(2)
col1.metric("Total DT Installed", dt_df["Installed"].sum())
col2.metric("Pending DT", dt_df["Pending"].sum())

# DT specific charts only

import pandas as pd
import streamlit as st

@st.cache_data
def load_and_prepare_data():
    df = pd.read_excel("data/meter_data.xlsx")

    # ---- STANDARDIZE ----
    df["date"] = pd.to_datetime(df["date"])

    # WC-MI data
    wc_df = df[df["Meter_Type"] == "WC-MI"].copy()

    # DT data
    dt_df = df[df["Meter_Type"] == "DT"].copy()

    return df, wc_df, dt_df

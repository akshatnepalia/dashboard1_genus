import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime
import os

# ===================== DB CONNECTION ===================== #
@st.cache_resource
def get_engine():
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    
    db_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}/{db_name}"
    return create_engine(db_url, pool_pre_ping=True)

# Load Data
@st.cache_data(ttl=600)
def load_data():
    engine = get_engine()
    query = "SELECT * FROM meter_data ORDER BY date ASC"
    return pd.read_sql(query, engine)

# ===================== Number Formatting ===================== #
def format_k(num):
    return f"{num/1000:.1f}k"

# ===================== Combined Graph + Table ===================== #
def graph_and_table(df):

    df["Total_Meters"] = df["WC_MI"] + df["DT"]
    df["Date"] = pd.to_datetime(df["date"])
    df = df.sort_values("Date")

    dates = df["Date"].dt.strftime("%d-%b")

    # ----- Plot ----- #
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dates, y=df["WC_MI"],
        name="WC-MI",
        marker_color="salmon",
        hovertemplate="WC-MI: %{y}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        x=dates, y=df["DT"],
        name="DT",
        marker_color="#FFD700",
        hovertemplate="DT: %{y}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=df["Total_Manpower"],
        name="Total Manpower",
        mode="lines+markers+text",
        marker=dict(color="#003366", size=8),
        text=df["Total_Manpower"],
        textposition="top center"
    ))

    # Put Total Meter values below bars
    fig.add_trace(go.Scatter(
        x=dates,
        y=[-300] * len(df),  # Slightly below zero baseline
        mode="text",
        text=[format_k(x) for x in df["Total_Meters"]],
        textposition="bottom center",
        showlegend=False
    ))

    fig.update_layout(
        barmode='stack',
        height=480,
        title="Daily Installed Meters vs Manpower",
        yaxis_title="Meters",
        xaxis_tickangle=-40,
        margin=dict(l=20, r=20, t=60, b=120)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------- Summary Table ---------- #
    table_df = df.set_index(dates)[[
        "Total_Meters", "WC_MI", "DT",
        "Total_Manpower", "CI", "MI", "IN_HOUSE", "Supervisory"
    ]]

    # Highlight rows
    table_df = table_df.style.format("{:,.0f}") \
        .set_properties(subset=["Total_Meters"], **{"background-color": "#e6f1ff", "font-weight": "bold"}) \
        .set_properties(subset=["Total_Manpower"], **{"background-color": "#e7f7e7", "font-weight": "bold"}) \
        .set_table_styles([{
            "selector": "th",
            "props": "background-color:#002b4d;color:white;font-weight:bold;"
        }])

    st.markdown("### 🧾 Date-wise Summary Table")
    st.dataframe(table_df, use_container_width=True)

# ===================== STREAMLIT UI ===================== #
st.set_page_config(layout="wide")
st.title("📊 Genus Power — Meter Installation Dashboard")

df = load_data()

col1, col2 = st.columns(2)
start = col1.date_input("Start Date", df["date"].min())
end = col2.date_input("End Date", df["date"].max())

mask = (pd.to_datetime(df["date"]) >= pd.to_datetime(start)) & \
       (pd.to_datetime(df["date"]) <= pd.to_datetime(end))
filtered = df[mask]

if filtered.empty:
    st.warning("No data available for the selected date range.")
else:
    graph_and_table(filtered)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime

# ========== PAGE SETTINGS ========== #
st.set_page_config(layout="wide")

# ========== CUSTOM CSS ========== #
st.markdown("""
<style>
    div.block-container { padding-top: 1rem; }
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)


# ========== DB ENGINE ========== #
@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)


# ========== INIT DB ========== #
@st.cache_data
def init_db():
    query = """
    CREATE TABLE IF NOT EXISTS meter_data (
        date DATE NOT NULL,
        package VARCHAR(20),
        wc_mi INTEGER,
        dt INTEGER,
        ci INTEGER,
        mi INTEGER,
        in_house INTEGER,
        supervisory INTEGER,
        UNIQUE(date, package)
    );
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(query))
        conn.commit()


init_db()


# ========== LOAD DATA ========== #
@st.cache_data(ttl=30)
def load_data():
    query = "SELECT * FROM meter_data ORDER BY date ASC"
    return pd.read_sql(query, get_engine())


# ========== ADMIN PANEL ========== #
def admin_panel():
    st.header("🔐 Admin Panel")
    st.write("Add new daily installation & manpower data")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if username == "admin" and password == "12345":
        st.success("Logged In ✔")

        st.subheader("➕ Insert New Data")

        date = st.date_input("Date", datetime.now())
        package = st.selectbox("Package", [
            "TN-95", "TN-96", "TN-97",
            "TN-58", "TN-59", "TN-60",
            "TN-32", "TN-33", "TN-34"
        ])
        wc_mi = st.number_input("WC-MI", min_value=0, value=0)
        dt = st.number_input("DT", min_value=0, value=0)
        ci = st.number_input("CI", min_value=0, value=0)
        mi = st.number_input("MI", min_value=0, value=0)
        ih = st.number_input("IN-HOUSE", min_value=0, value=0)
        sup = st.number_input("Supervisory", min_value=0, value=0)

        if st.button("Add Data"):
            try:
                engine = get_engine()
                query = """
                INSERT INTO meter_data (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
                VALUES (:date, :package, :wc_mi, :dt, :ci, :mi, :ih, :sup)
                ON CONFLICT (date, package) DO UPDATE SET
                wc_mi = EXCLUDED.wc_mi,
                dt = EXCLUDED.dt,
                ci = EXCLUDED.ci,
                mi = EXCLUDED.mi,
                in_house = EXCLUDED.in_house,
                supervisory = EXCLUDED.supervisory;
                """
                with engine.connect() as conn:
                    conn.execute(text(query), {
                        "date": date, "package": package, "wc_mi": wc_mi, "dt": dt,
                        "ci": ci, "mi": mi, "ih": ih, "sup": sup
                    })
                    conn.commit()
                load_data.clear()
                st.success("Data saved successfully! ✔")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        if username or password:
            st.error("Incorrect credentials ❌")


# ========== GRAPH + TABLE VIEW ========== #
def graph_and_table(df):
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    df["Toolkit"] = (df["Total_WC_DT"] / df["Total_Manpower"]).fillna(0).round(2)

    full_dates = pd.date_range(df["date"].min(), df["date"].max()).date
    df = df.groupby("date").sum().reindex(full_dates, fill_value=0).reset_index()

    # KPIs
    total_meters = df["Total_WC_DT"].sum()
    pk_i = df["Total_WC_DT"].idxmax()
    pk_m = df["Total_Manpower"].idxmax()

    k1, k2, k3 = st.columns(3)
    k1.metric("📦 Total Meters (WC+DT)", f"{total_meters:,}")
    k2.metric("📈 Peak Installation (Meters)", f"{int(df.loc[pk_i,'Total_WC_DT'])} on {df.loc[pk_i,'date'].strftime('%d-%b')}")
    k3.metric("👥 Peak Manpower", f"{int(df.loc[pk_m,'Total_Manpower'])} on {df.loc[pk_m,'date'].strftime('%d-%b')}")

    # Chart
    fig = go.Figure()
    fig.add_bar(x=df["date"], y=df["wc_mi"], name="WC-MI", marker_color="#FF7B7B")
    fig.add_bar(x=df["date"], y=df["dt"], name="DT", marker_color="#FFD700")

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Total_Manpower"],
        mode="lines+markers+text", name="Manpower",
        text=[str(int(x)) for x in df["Total_Manpower"]],
        yaxis="y2"
    ))

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["Total_WC_DT"],
        mode="lines+markers", name="Total Meters", yaxis="y2"
    ))

    fig.update_layout(
        height=550,
        barmode="stack",
        xaxis=dict(
            tickvals=full_dates,
            ticktext=[d.strftime("%d-%b") for d in full_dates],
            tickangle=45
        ),
        yaxis2=dict(overlaying="y", side="right")
    )
    st.plotly_chart(fig, use_container_width=True)

    # Table
    table = df.set_index("date")[[
        "Total_WC_DT", "wc_mi", "dt", "Total_Manpower",
        "ci", "mi", "in_house", "supervisory"
    ]]

    # Fix Index Error
    table.index = pd.to_datetime(table.index, errors="coerce")
    table.index = table.index.strftime("%d-%b")

    table = table.T

    table.index = [
        "🔷 Total Meters", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    st.subheader("📋 Table Summary")
    st.dataframe(table, use_container_width=True)


# ========== DASHBOARD VIEW ========== #
def dashboard_view():
    st.markdown("""<div style='text-align:center'>
        <span style='font-size:40px;font-weight:800;color:#003A8C;'>Genus Power Infrastructures Ltd.</span>
        <div style='background:#FFD700;height:4px;width:260px;margin:auto;margin-top:6px;'></div>
        <h4 style='font-weight:700;margin-top:8px;'>📊 Meter Dashboard — WC/DT + Manpower</h4>
    </div>""", unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("⚠ No data found in database.")
        return

    st.markdown("### 🔍 Filters")
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        view = st.radio("View Mode", ["Combined View", "Package Wise View"], horizontal=True)

    with c2:
        start_date = st.date_input("Start Date", df["date"].min())

    with c3:
        end_date = st.date_input("End Date", df["date"].max())

    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    if view == "Combined View":
        graph_and_table(df)

    else:
        package = st.selectbox("Select Package", sorted(df["package"].unique()))
        graph_and_table(df[df["package"] == package])


# ========== SIDEBAR NAVIGATION ========== #
menu = st.sidebar.radio("📌 Navigation", ["Dashboard", "Admin Panel"])

if menu == "Dashboard":
    dashboard_view()
else:
    admin_panel()

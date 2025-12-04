import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os
from datetime import datetime

# ================= DB CONNECTION ================= #
@st.cache_resource
def get_engine():
    db_url = os.getenv("DB_URL")
    return create_engine(db_url, pool_pre_ping=True)

# ================= DB TABLE SETUP ================= #
@st.cache_resource
def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS meter_data (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            package VARCHAR(10) NOT NULL,
            wc_mi INT DEFAULT 0,
            dt INT DEFAULT 0,
            ci INT DEFAULT 0,
            mi INT DEFAULT 0,
            in_house INT DEFAULT 0,
            supervisory INT DEFAULT 0,
            UNIQUE(date, package)
        );
        """))
    return True

init_db()

# ================= DATA HELPERS ================= #
@st.cache_data(ttl=10)
def load_data():
    engine = get_engine()
    query = "SELECT * FROM meter_data ORDER BY date ASC"
    df = pd.read_sql(query, engine)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["total_meters"] = df["wc_mi"] + df["dt"]
        df["total_manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    return df

def insert_data(values):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO meter_data 
            (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
            VALUES (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
            ON CONFLICT (date, package)
            DO UPDATE SET wc_mi = excluded.wc_mi,
                          dt = excluded.dt,
                          ci = excluded.ci,
                          mi = excluded.mi,
                          in_house = excluded.in_house,
                          supervisory = excluded.supervisory;
        """), values)
    st.success("Data saved successfully!")
    st.cache_data.clear()

# ================= CUSTOM FORMATTER ================= #
def fmt_k(v):
    return f"{v/1000:.1f}k"

# ================= ADMIN PANEL ================= #
def admin_panel():
    st.title("🔐 Admin Panel")

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

    if login_btn:
        if username == "admin" and password == "12345":
            st.session_state.logged = True
            st.success("Logged In ✓")
        else:
            st.error("Invalid credentials")

    if st.session_state.get("logged"):
        st.subheader("➕ Insert New Data")

        with st.form("insert_form"):
            date = st.date_input("Date")
            package = st.selectbox("Package",
                ["TN-95","TN-96","TN-97","TN-58","TN-59","TN-60","TN-32","TN-33","TN-34"]
            )
            wc_mi = st.number_input("WC-MI", 0)
            dt = st.number_input("DT", 0)
            ci = st.number_input("CI", 0)
            mi = st.number_input("MI", 0)
            in_house = st.number_input("IN-HOUSE", 0)
            supervisory = st.number_input("Supervisory", 0)

            submitted = st.form_submit_button("Submit")
            if submitted:
                insert_data({
                    "date": date,
                    "package": package,
                    "wc_mi": wc_mi,
                    "dt": dt,
                    "ci": ci,
                    "mi": mi,
                    "in_house": in_house,
                    "supervisory": supervisory,
                })

# ================= PLOT + TABLE ================= #
def graph_and_table(df):
    df_grouped = df.groupby("date", as_index=False).sum()

    fig = go.Figure()

    # WC-MI Bars with bottom labels in K format
    fig.add_bar(
        x=df_grouped["date"],
        y=df_grouped["wc_mi"],
        name="WC-MI",
        marker_color="#FF6F6F",
        text=[fmt_k(x) for x in df_grouped["wc_mi"]],
        textposition="outside",
        textfont=dict(size=12, color="black")
    )

    fig.add_bar(
        x=df_grouped["date"],
        y=df_grouped["dt"],
        name="DT",
        marker_color="#FFD700"
    )

    fig.add_trace(go.Scatter(
        x=df_grouped["date"],
        y=df_grouped["total_manpower"],
        name="Total Manpower",
        mode="lines+markers+text",
        marker=dict(color="navy", size=9),
        text=df_grouped["total_manpower"],
        textposition="top center"
    ))

    fig.update_layout(
        barmode="stack",
        height=600,
        xaxis_title="Date",
        yaxis_title="Meters",
        legend_title="Legend"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Data Table")
    st.dataframe(df_grouped.style.format({"total_meters": "{:,}", "total_manpower": "{:,}"}))

# ================= DASHBOARD ================= #
def show_dashboard():
    st.title("📊 Genus Meter Dashboard — WC/DT + Manpower")

    df = load_data()
    if df.empty:
        st.warning("No data available")
        return

    total_m = df["total_meters"].sum()
    peak_meters = df.loc[df["total_meters"].idxmax()]
    peak_mnp = df.loc[df["total_manpower"].idxmax()]

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Meters", f"{total_m:,}")
    col2.metric("📈 Peak Installation", f"{peak_meters['total_meters']:,}", peak_meters['date'].strftime("%d-%b"))
    col3.metric("👥 Peak Manpower", f"{peak_mnp['total_manpower']:,}", peak_mnp['date'].strftime("%d-%b"))

    graph_and_table(df)

# ================= MAIN PAGE ================= #
st.sidebar.title("Navigation")
choice = st.sidebar.radio("Go to:",
                         ["Admin Panel", "Dashboard"])

if choice == "Admin Panel":
    admin_panel()
else:
    show_dashboard()

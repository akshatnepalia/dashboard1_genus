import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ==================== PAGE CONFIG ==================== #
st.set_page_config(layout="wide", page_title="Meter Dashboard")

# ==================== DATABASE ==================== #
DB_URL = st.secrets["DB_URL"]
engine = create_engine(DB_URL)

@st.cache_data(ttl=60)
def load_data():
    query = "SELECT * FROM meter_data ORDER BY date ASC"
    return pd.read_sql(query, engine)

# ==================== CUSTOM CSS ==================== #
st.markdown("""
<style>
div.block-container {padding-top: 1rem;}
thead tr th {background-color: #003A8C !important; color:white !important;}
</style>
""", unsafe_allow_html=True)

# ==================== HEADER ==================== #
st.markdown("""
<div style='text-align:center;'>
    <h1 style='color:#003A8C;'>Genus Power Infrastructures Ltd.</h1>
    <div style='width:260px;height:4px;margin:4px auto;background:#FFD700;border-radius:4px;'></div>
    <h4>📊 Meter Dashboard — WC/DT + Manpower</h4>
</div>
""", unsafe_allow_html=True)

# ==================== SIDEBAR NAVIGATION ==================== #
menu = st.sidebar.radio("📌 Navigation", ["Dashboard", "Admin"])

# ==================== DASHBOARD PAGE ==================== #
if menu == "Dashboard":

    df = load_data()
    df["date"] = pd.to_datetime(df["date"])
    df["Total_Manpower"] = df[["ci","mi","in_house","supervisory"]].sum(axis=1)
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]

    full_dates = pd.date_range(df["date"].min(), df["date"].max())

    st.write("### 🔍 Filters")
    view = st.radio("View Mode", ["Combined View", "Package Wise View"], horizontal=True)

    start_date, end_date = st.date_input(
        "Select Date Range", [df["date"].min(), df["date"].max()]
    )

    df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    if view == "Package Wise View":
        pkg = st.selectbox("Select Package", sorted(df["package"].unique()))
        df_filtered = df_filtered[df_filtered["package"] == pkg]

    # Summation by date
    data = df_filtered.groupby("date").sum().reindex(full_dates, fill_value=0)
    data.reset_index(inplace=True)
    data.rename(columns={"index": "date"}, inplace=True)

    # KPI Calculation
    total_mtr = data["Total_WC_DT"].sum()
    peak_idx = data["Total_WC_DT"].idxmax()
    peak_label = data.loc[peak_idx, "date"].strftime("%d-%b")

    mp_peak_idx = data["Total_Manpower"].idxmax()
    mp_peak_label = data.loc[mp_peak_idx, "date"].strftime("%d-%b")

    # KPI CARDS
    k1, k2, k3 = st.columns(3)
    k1.metric("📦 Total Meters Installed", f"{total_mtr:,}")
    k2.metric("🚀 Peak Installation Day", peak_label)
    k3.metric("👥 Peak Manpower Day", mp_peak_label)

    # ==================== GRAPH ==================== #
    fig = go.Figure()

    hover = (
        "Date: %{x|%d-%b}<br>WC-MI: %{customdata[6]}<br>DT: %{customdata[7]}<br>"
        "Total Meters: %{customdata[5]}<br><br>"
        "CI: %{customdata[1]}<br>MI: %{customdata[2]}<br>IN-HOUSE: %{customdata[3]}<br>"
        "Supervisory: %{customdata[4]}<br>Total Manpower: %{customdata[0]}<extra></extra>"
    )

    fig.add_trace(go.Bar(
        x=data["date"], y=data["wc_mi"], name="WC-MI",
        marker_color="#FF7B7B", customdata=data[
            ["Total_Manpower","ci","mi","in_house","supervisory","Total_WC_DT","wc_mi","dt"]
        ],
        hovertemplate=hover
    ))
    fig.add_trace(go.Bar(
        x=data["date"], y=data["dt"], name="DT",
        marker_color="#FFD700", customdata=data[
            ["Total_Manpower","ci","mi","in_house","supervisory","Total_WC_DT","wc_mi","dt"]
        ],
        hovertemplate=hover
    ))
    fig.add_trace(go.Scatter(
        x=data["date"], y=data["Total_Manpower"], name="Total Manpower",
        mode="lines+markers+text", text=[str(int(v)) for v in data["Total_Manpower"]],
        textposition="top center",
        line=dict(color="#003A8C", width=3), marker=dict(size=8)
    ))

    fig.update_layout(
        barmode="stack", height=550,
        xaxis=dict(
            tickvals=full_dates,
            ticktext=[d.strftime("%d-%b") for d in full_dates],
            tickangle=45
        ),
        yaxis2=dict(overlaying="y", side="right")
    )

    st.plotly_chart(fig, use_container_width=True)

    # TABLE
    table = data.set_index("date")[
        ["Total_WC_DT","wc_mi","dt","Total_Manpower","ci","mi","in_house","supervisory"]
    ]
    table.index = table.index.strftime("%d-%b")
    table = table.T.astype(int)

    st.subheader("📋 Date-wise Summary")
    st.dataframe(table, use_container_width=True)


# ==================== ADMIN PAGE ==================== #
else:
    st.markdown("## 🔐 Admin Panel")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "12345":
            st.success("Logged In ✔")

            with st.form("insert_form"):
                st.write("### ➕ Insert New Data")

                date = st.date_input("Date")
                package = st.text_input("Package")
                wc_mi = st.number_input("WC-MI", min_value=0)
                dt = st.number_input("DT", min_value=0)
                ci = st.number_input("CI", min_value=0)
                mi = st.number_input("MI", min_value=0)
                ih = st.number_input("IN-HOUSE", min_value=0)
                sup = st.number_input("Supervisory", min_value=0)

                submitted = st.form_submit_button("Save")

                if submitted:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO meter_data (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
                            VALUES (:d, :p, :w, :dt, :c, :m, :ih, :s)
                        """), dict(d=date, p=package, w=wc_mi, dt=dt, c=ci, m=mi, ih=ih, s=sup))

                    st.success("Record Added Successfully 🎯")
                    st.cache_data.clear()
        else:
            st.error("Invalid Credentials ❌")

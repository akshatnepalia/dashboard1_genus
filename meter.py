import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import date

# ====== PAGE CONFIG ====== #
st.set_page_config(layout="wide", page_title="Genus Dashboard")

# ====== STYLES ====== #
st.markdown("""
<style>
body {font-family: "Arial";}
.kpi-card {
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    color: white;
    font-size: 18px;
    font-weight: 700;
}
thead tr th {
    background-color: #003A8C !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# ====== DATABASE CONNECTION ====== #
engine = create_engine(st.secrets["DB_URL"])

# ====== AUTH STATE ====== #
if "auth" not in st.session_state:
    st.session_state.auth = False


# ====== LOGIN PAGE ====== #
def login_page():
    st.markdown("## 🔐 Admin Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == st.secrets["ADMIN"]["USER"] and pwd == st.secrets["ADMIN"]["PASS"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")


# ====== DATA LOAD FUNCTION ====== #
@st.cache_data
def load_data():
    df = pd.read_sql("SELECT * FROM meter_data ORDER BY date ASC", engine)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    numeric_cols = ["wc_mi","dt","ci","mi","in_house","supervisory"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df


# ====== ADMIN PANEL ====== #
def admin_panel():
    st.title("🛠️ Admin Data Entry")
    df = load_data()

    st.subheader("Add New Record")

    col1, col2, col3 = st.columns(3)
    with col1:
        pkg = st.text_input("Package")
    with col2:
        dt_selected = st.date_input("Date", date.today())
    with col3:
        wc_mi = st.number_input("WC-MI", min_value=0)

    col4, col5, col6, col7 = st.columns(4)
    ci = col4.number_input("CI", min_value=0)
    mi = col5.number_input("MI", min_value=0)
    inh = col6.number_input("IN-HOUSE", min_value=0)
    sup = col7.number_input("Supervisory", min_value=0)

    if st.button("➕ Insert Record"):
        query = """
            INSERT INTO meter_data (package, date, wc_mi, dt, ci, mi, in_house, supervisory)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        engine.execute(query, (pkg, dt_selected, wc_mi, 0, ci, mi, inh, sup))
        st.success("Record added successfully!")
        st.cache_data.clear()
        st.rerun()


# ====== DASHBOARD ====== #
def dashboard():
    # Header
    st.markdown("""
    <h2 style='text-align:center;color:#003A8C;font-weight:800;'>Genus Power Infrastructures Ltd.</h2>
    <hr style="border:2px solid #FFD700; width:250px; margin:auto;">
    """, unsafe_allow_html=True)

    df = load_data()

    # Filters
    colA, colB, colC = st.columns([2,1,1])
    with colA:
        view = st.radio("View Mode", ["Combined", "Package Wise"], horizontal=True)
    with colB:
        start = st.date_input("Start Date", df["date"].min())
    with colC:
        end = st.date_input("End Date", df["date"].max())

    df_f = df[(df["date"]>=start) & (df["date"]<=end)]

    package = None
    if view == "Package Wise":
        package = st.selectbox("Select Package", sorted(df["package"].unique()))
        df_f = df_f[df_f["package"] == package]

    full_dates = pd.date_range(start, end).date
    df_f = df_f.groupby("date").sum().reindex(full_dates, fill_value=0).reset_index()
    df_f.rename(columns={"index": "date"}, inplace=True)

    # KPI
    total_m = df_f["Total_WC_DT"].sum()
    peak_i = df_f.iloc[df_f["Total_WC_DT"].idxmax()]
    peak_p = df_f.iloc[df_f["Total_Manpower"].idxmax()]

    c1, c2, c3 = st.columns(3)
    c1.write(f"<div class='kpi-card' style='background:#003A8C;'>📦 Total Meters<br>{total_m:,}</div>", unsafe_allow_html=True)
    c2.write(f"<div class='kpi-card' style='background:#009688;'>📈 Peak Install<br>{peak_i['Total_WC_DT']} on {peak_i['date']}</div>", unsafe_allow_html=True)
    c3.write(f"<div class='kpi-card' style='background:#D32F2F;'>👥 Peak Manpower<br>{peak_p['Total_Manpower']} on {peak_p['date']}</div>", unsafe_allow_html=True)

    # Graph
    fig = go.Figure()
    fig.add_bar(x=df_f["date"], y=df_f["wc_mi"], name="WC-MI", marker_color="#FF7B7B")
    fig.add_bar(x=df_f["date"], y=df_f["dt"], name="DT", marker_color="#FFD700")
    fig.add_scatter(x=df_f["date"], y=df_f["Total_Manpower"], mode="lines+markers+text",
                    text=[str(int(x)) for x in df_f["Total_Manpower"]],
                    textposition="top center",
                    line=dict(color="#003A8C", width=3))
    fig.update_layout(height=480, barmode="stack")
    st.plotly_chart(fig, use_container_width=True)

    # Table
    table = df_f.set_index("date")[["Total_WC_DT","wc_mi","dt","Total_Manpower","ci","mi","in_house","supervisory"]]
    table.index = table.index.map(lambda x: x.strftime("%d-%b"))
    st.dataframe(table.style.highlight_max(axis=1), use_container_width=True)


# ===== NAVIGATION ===== #
if st.session_state.auth:
    menu = st.sidebar.radio("📌 Navigation", ["Dashboard", "Admin Panel", "Logout"])
    if menu == "Dashboard": dashboard()
    elif menu == "Admin Panel": admin_panel()
    elif menu == "Logout":
        st.session_state.auth = False
        st.rerun()
else:
    login_page()

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import date

# ===================== BASIC CONFIG ===================== #
st.set_page_config(page_title="Genus Meter Dashboard",
                   layout="wide",
                   initial_sidebar_state="expanded")

# ---------- CSS ---------- #
st.markdown("""
<style>
    div.block-container {padding-top: 1.2rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
    .kpi-card {
        padding: 0.8rem 1rem;
        border-radius: 0.9rem;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #111827;
    }
</style>
""", unsafe_allow_html=True)

# ===================== HEADER ===================== #
st.markdown("""
<div style='text-align:center;margin-bottom:0.5rem;'>
    <span style='font-size:42px;font-weight:800;color:#003A8C;'>
        Genus Power Infrastructures Ltd.
    </span>
    <div style='width:260px;height:4px;margin:6px auto;
                background: linear-gradient(to right,#003A8C,#FFD700);
                border-radius:4px;'></div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<h4 style='text-align:center;font-weight:700;margin-top:0.1rem;margin-bottom:0.8rem;'>
📊 Meter Dashboard — WC/DT + Manpower
</h4>
""", unsafe_allow_html=True)

# ===================== CONSTANTS ===================== #
ALLOWED_PACKAGES = [
    "TN-95", "TN-96", "TN-97",
    "TN-58", "TN-59", "TN-60",
    "TN-32", "TN-33", "TN-34",
]

ADMIN_USER = st.secrets.get("ADMIN_USER", "admin")
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "12345")

# ===================== DB CONNECTION ===================== #
@st.cache_resource
def get_engine():
    db_url = st.secrets["DB_URL"]
    return create_engine(db_url, pool_pre_ping=True)


@st.cache_resource
def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS meter_data (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                package TEXT NOT NULL,
                wc_mi INTEGER DEFAULT 0,
                dt INTEGER DEFAULT 0,
                ci INTEGER DEFAULT 0,
                mi INTEGER DEFAULT 0,
                in_house INTEGER DEFAULT 0,
                supervisory INTEGER DEFAULT 0
            );
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_unique
            ON meter_data(date, package);
        """))
    return True


@st.cache_data
def load_data():
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM meter_data ORDER BY date ASC", engine)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    for c in ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]

    return df


def clear_cache():
    load_data.clear()


def upsert_row(row):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO meter_data
              (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
            VALUES
              (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
            ON CONFLICT (date, package)
            DO UPDATE SET
              wc_mi = EXCLUDED.wc_mi,
              dt = EXCLUDED.dt,
              ci = EXCLUDED.ci,
              mi = EXCLUDED.mi,
              in_house = EXCLUDED.in_house,
              supervisory = EXCLUDED.supervisory;
        """), row)
    clear_cache()


def kfmt(v):
    return f"{v/1000:.1f}k" if v >= 1000 else str(v)


init_db()

# ===================== NAVIGATION ===================== #
mode = st.sidebar.radio("🔀 Navigate", ["Dashboard", "Admin Panel"])

# ====================================================== #
#                       DASHBOARD                        #
# ====================================================== #
def graph_and_table(df_view):

    total_meters = df_view["Total_WC_DT"].sum()
    total_manpower = df_view["Total_Manpower"].sum()

    # KPI metrics
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class='kpi-card'>
        <div class='kpi-label'>📦 Total Meters Installed</div>
        <div class='kpi-value'>{kfmt(total_meters)}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='kpi-card'>
        <div class='kpi-label'>👥 Total Manpower</div>
        <div class='kpi-value'>{kfmt(total_manpower)}</div>
        </div>""", unsafe_allow_html=True)

    # Chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_view["date"],
        y=df_view["wc_mi"],
        name="WC-MI",
        marker_color="#FF7B7B"
    ))

    fig.add_trace(go.Bar(
        x=df_view["date"],
        y=df_view["dt"],
        name="DT",
        marker_color="#FFD700"
    ))

    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=df_view["Total_WC_DT"],
        mode="text",
        text=[kfmt(v) for v in df_view["Total_WC_DT"]],
        textposition="bottom center",
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=df_view["Total_Manpower"],
        name="Total Manpower",
        mode="lines+markers",
        marker=dict(color="#003A8C"),
        yaxis="y2"
    ))

    fig.update_layout(
        height=540,
        barmode="stack",
        hovermode="closest",
        xaxis=dict(tickangle=45),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Table
    table = df_view.set_index("date")[[
        "Total_WC_DT", "wc_mi", "dt",
        "Total_Manpower", "ci", "mi", "in_house", "supervisory"
    ]]

    table.index = pd.to_datetime(table.index).strftime("%d-%b")
    table = table.T

    table.index = [
        "🔷 Total Meters (WC+DT)", "WC-MI", "DT",
        "🟢 Total Manpower", "CI", "MI", "IN-HOUSE", "Supervisory"
    ]

    def highlight(r):
        if r.name.startswith("🔷") or r.name.startswith("🟢"):
            return ["background-color:#D4F0FF;font-weight:bold"] * len(r)
        return [""] * len(r)

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(table.style.apply(highlight, axis=1),
                 use_container_width=True)


def show_dashboard():
    df = load_data()
    if df.empty:
        st.info("⛔ No data available yet.")
        return

    st.markdown("### 🔍 Filters")
    col1, col2, col3 = st.columns([2,1,1])

    with col1:
        view = st.radio("View Mode", ["Combined View", "Package Wise View"],
                        horizontal=True)

    min_d, max_d = df["date"].min(), df["date"].max()

    with col2:
        start = st.date_input("Start Date", min_d, min_value=min_d, max_value=max_d)
    with col3:
        end = st.date_input("End Date", max_d, min_value=min_d, max_value=max_d)

    m = (df["date"] >= start) & (df["date"] <= end)
    df_r = df[m]

    if view == "Combined View":
        grp = df_r.groupby("date").sum().reset_index()
    else:
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)
        grp = df_r[df_r["package"] == pkg].groupby("date").sum().reset_index()

    graph_and_table(grp)

# ====================================================== #
#                        ADMIN PANEL                     #
# ====================================================== #
def show_admin():
    st.markdown("## 🔐 Admin Panel")

    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == ADMIN_USER and p == ADMIN_PASS:
                    st.session_state.is_admin = True
                    st.success("Authorized ✔")
                else:
                    st.error("Wrong credentials ❌")
        return

    st.success("Logged In ✔")

    with st.expander("➕ Insert New Data", expanded=True):
        d = st.date_input("Date", date.today())
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)

        wc = st.number_input("WC-MI", 0)
        dtv = st.number_input("DT", 0)
        ci = st.number_input("CI", 0)
        mi = st.number_input("MI", 0)
        ih = st.number_input("IN-HOUSE", 0)
        sp = st.number_input("Supervisory", 0)

        if st.button("Save / Update"):
            upsert_row(dict(
                date=d, package=pkg, wc_mi=wc, dt=dtv,
                ci=ci, mi=mi, in_house=ih, supervisory=sp
            ))
            st.success("Saved ✔")

    df = load_data()
    if not df.empty:
        st.subheader("🧾 Latest 20 Rows")
        st.dataframe(df.sort_values("date", ascending=False).head(20),
                     use_container_width=True)

# ===================== MAIN ===================== #
if mode == "Dashboard":
    show_dashboard()
else:
    show_admin()

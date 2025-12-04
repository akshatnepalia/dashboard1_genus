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
📊 Meter Dashboard — WC/DT + Manpower (Toolkit Restored)
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
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine


@st.cache_resource
def init_db():
    engine = get_engine()
    ddl = """
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
    CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_unique
    ON meter_data(date, package);
    """
    with engine.begin() as conn:
        for stmt in ddl.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
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

    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]

    return df


def clear_cache():
    load_data.clear()


def upsert_row(row):
    engine = get_engine()
    stmt = text("""
        INSERT INTO meter_data(date, package, wc_mi, dt, ci, mi, in_house, supervisory)
        VALUES(:date,:package,:wc_mi,:dt,:ci,:mi,:in_house,:supervisory)
        ON CONFLICT(date,package) DO UPDATE SET
            wc_mi=EXCLUDED.wc_mi, dt=EXCLUDED.dt,
            ci=EXCLUDED.ci, mi=EXCLUDED.mi,
            in_house=EXCLUDED.in_house, supervisory=EXCLUDED.supervisory
    """)
    with engine.begin() as conn:
        conn.execute(stmt, row)
    clear_cache()


def kfmt(v): return f"{v/1000:.1f}k" if v >= 1000 else str(v)


# Ensure DB ready
init_db()


# ====================================================== #
#   📊 DASHBOARD CHART + TABLE                           #
# ====================================================== #
def graph_and_table(df_view):
    if df_view.empty:
        st.info("No data found for selected filters.")
        return

    # ---------- KPIs ---------- #
    total_meters = int(df_view["Total_WC_DT"].sum())
    peak_m = df_view.loc[df_view["Total_WC_DT"].idxmax()]
    peak_mp = df_view.loc[df_view["Total_Manpower"].idxmax()]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>📦 Total Meters (WC+DT)</div><div class='kpi-value'>{kfmt(total_meters)}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>📈 Peak Install</div><div class='kpi-value'>{int(peak_m['Total_WC_DT'])} on {peak_m['date'].strftime('%d-%b')}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>🧑‍🔧 Peak Manpower</div><div class='kpi-value'>{int(peak_mp['Total_Manpower'])} on {peak_mp['date'].strftime('%d-%b')}</div></div>", unsafe_allow_html=True)

    # ---------- Chart ---------- #
    hovertemplate = (
        "Date: %{x}<br><br>"
        "Total Manpower: %{customdata[0]}<br>"
        "CI: %{customdata[1]}<br>"
        "MI: %{customdata[2]}<br>"
        "IN-HOUSE: %{customdata[3]}<br>"
        "Supervisory: %{customdata[4]}<br><br>"
        "Toolkit: %{customdata[8]}<br>"
        "Total Meters: %{customdata[5]}<br>"
        "WC-MI: %{customdata[6]}<br>"
        "DT: %{customdata[7]}<br>"
        "<extra></extra>"
    )

    df_view["Toolkit"] = df_view["wc_mi"] + df_view["dt"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_view["date"], y=df_view["wc_mi"], name="WC-MI", marker_color="#FF7B7B",
        customdata=df_view[["Total_Manpower","ci","mi","in_house","supervisory",
                           "Total_WC_DT","wc_mi","dt","Toolkit"]],
        hovertemplate=hovertemplate
    ))

    fig.add_trace(go.Bar(
        x=df_view["date"], y=df_view["dt"], name="DT", marker_color="#FFD700",
        customdata=df_view[["Total_Manpower","ci","mi","in_house","supervisory",
                           "Total_WC_DT","wc_mi","dt","Toolkit"]],
        hovertemplate=hovertemplate
    ))

    fig.add_trace(go.Scatter(
        x=df_view["date"], y=df_view["Total_Manpower"],
        name="Total Manpower", mode="lines+markers+text",
        text=[int(x) for x in df_view["Total_Manpower"]],
        textposition="top center", marker=dict(size=9, color="#003A8C"),
        line=dict(color="#003A8C", width=3), yaxis="y2",
        hoverinfo="skip"
    ))

    # ===== NEW: K-Value under bars ===== #
    fig.add_trace(go.Scatter(
        x=df_view["date"], y=[-50]*len(df_view),
        mode="text",
        text=[kfmt(v) for v in df_view["Total_WC_DT"]],
        textposition="bottom center",
        textfont=dict(size=11, color="#111827"),
        hoverinfo="skip", showlegend=False
    ))

    fig.update_layout(
        height=580,
        barmode="stack",
        xaxis=dict(tickangle=45),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", side="right", overlaying="y"),
        margin=dict(b=90),
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center")
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------- TABLE ---------- #
    table = df_view.set_index("date")[["Total_WC_DT","wc_mi","dt",
                                       "Total_Manpower","ci","mi",
                                       "in_house","supervisory"]]
    table.index = table.index.strftime("%d-%b")
    table = table.T

    table.index = ["🔷 Total Meters","WC-MI","DT","🟢 Total Manpower",
                   "CI","MI","IN-HOUSE","Supervisory"]
    st.subheader("📋 Daily Summary")
    st.dataframe(table, use_container_width=True)


# ====================================================== #
#                      FILTER UI                         #
# ====================================================== #
def show_dashboard():
    df = load_data()
    if df.empty:
        st.warning("No Data! Add_meter records in Admin Panel ⬅")
        return

    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        view = st.radio("View Mode", ["Combined View","Package Wise"], horizontal=True)

    min_d, max_d = df["date"].min(), df["date"].max()
    with col2:
        sd = st.date_input("Start Date", min_d)
    with col3:
        ed = st.date_input("End Date", max_d)

    if sd > ed:
        st.error("Invalid date selection")
        return

    df_range = df[(df["date"]>=sd)&(df["date"]<=ed)]

    if view=="Combined View":
        grp = df_range.groupby("date").sum().reset_index()
        graph_and_table(grp)
    else:
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)
        grp = df_range[df_range["package"]==pkg].groupby("date").sum().reset_index()
        graph_and_table(grp)


# ====================================================== #
#                       ADMIN UI                         #
# ====================================================== #
def show_admin():
    st.header("Admin Panel 🔐")

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login") and u==ADMIN_USER and p==ADMIN_PASS:
            st.session_state.auth = True
            st.success("Welcome Admin! 🔑")
        return

    with st.expander("Add Single Entry"):
        d = st.date_input("Date", date.today())
        pkg = st.selectbox("Package", ALLOWED_PACKAGES)
        wc = st.number_input("WC-MI",0)
        dt = st.number_input("DT",0)
        ci = st.number_input("CI",0)
        mi = st.number_input("MI",0)
        ih = st.number_input("IN-HOUSE",0)
        sp = st.number_input("Supervisory",0)

        if st.button("Save / Update"):
            upsert_row(dict(date=d,package=pkg,wc_mi=wc,dt=dt,
                            ci=ci,mi=mi,in_house=ih,supervisory=sp))
            st.success("Saved!")

    df_preview = load_data().tail(20)
    st.subheader("Latest Records")
    st.dataframe(df_preview, use_container_width=True)


# ===================== MAIN ===================== #
mode = st.sidebar.radio("Navigate", ["Dashboard","Admin Panel"])
if mode=="Dashboard": show_dashboard()
else: show_admin()

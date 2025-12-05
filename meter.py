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
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine


@st.cache_resource
def init_db():
    engine = get_engine()
    ddl_table = """
    CREATE TABLE IF NOT EXISTS meter_data (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        package TEXT NOT NULL,
        wc_mi INTEGER NOT NULL DEFAULT 0,
        dt INTEGER NOT NULL DEFAULT 0,
        ci INTEGER NOT NULL DEFAULT 0,
        mi INTEGER NOT NULL DEFAULT 0,
        in_house INTEGER NOT NULL DEFAULT 0,
        supervisory INTEGER NOT NULL DEFAULT 0
    );
    """
    ddl_index = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_date_package
    ON meter_data(date, package);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl_table))
        conn.execute(text(ddl_index))
    return True


@st.cache_data
def load_data():
    engine = get_engine()
    query = """
    SELECT date, package, wc_mi, dt, ci, mi, in_house, supervisory
    FROM meter_data
    ORDER BY date ASC;
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"]).dt.date
    num_cols = ["wc_mi", "dt", "ci", "mi", "in_house", "supervisory"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    return df


def clear_cache():
    load_data.clear()


def upsert_row(row):
    engine = get_engine()
    stmt = text("""
        INSERT INTO meter_data
        (date, package, wc_mi, dt, ci, mi, in_house, supervisory)
        VALUES (:date, :package, :wc_mi, :dt, :ci, :mi, :in_house, :supervisory)
        ON CONFLICT (date, package)
        DO UPDATE SET
            wc_mi = EXCLUDED.wc_mi,
            dt = EXCLUDED.dt,
            ci = EXCLUDED.ci,
            mi = EXCLUDED.mi,
            in_house = EXCLUDED.in_house,
            supervisory = EXCLUDED.supervisory;
    """)
    with engine.begin() as conn:
        conn.execute(stmt, row)
    clear_cache()


def kfmt(v): return f"{v/1000:.1f}k" if v >= 1000 else str(int(v))


init_db()

# ===================== NAVIGATION ===================== #
mode = st.sidebar.radio("🔀 Navigate", ["Dashboard", "Admin Panel"])

# ===================== DASHBOARD ===================== #
def graph_and_table(df_view):
    if df_view.empty:
        st.info("No data available.")
        return

    # KPIs
    total_meters = int(df_view["Total_WC_DT"].sum())
    peak_idx = df_view["Total_WC_DT"].idxmax()
    peak_label = f"{int(df_view.loc[peak_idx,'Total_WC_DT'])} on {df_view.loc[peak_idx,'date'].strftime('%d-%b')}"
    
    pm_idx = df_view["Total_Manpower"].idxmax()
    pm_label = f"{int(df_view.loc[pm_idx,'Total_Manpower'])} on {df_view.loc[pm_idx,'date'].strftime('%d-%b')}"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>📦 Total Meters</div><div class='kpi-value'>{kfmt(total_meters)}</div></div>",unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>📈 Peak Installation</div><div class='kpi-value'>{peak_label}</div></div>",unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'>👥 Peak Manpower</div><div class='kpi-value'>{pm_label}</div></div>",unsafe_allow_html=True)

    fig = go.Figure()

    # WC-MI
    fig.add_trace(go.Bar(x=df_view["date"],y=df_view["wc_mi"],
        name="WC-MI", marker_color="#FF7B7B"
    ))

    # DT
    fig.add_trace(go.Bar(x=df_view["date"],y=df_view["dt"],
        name="DT", marker_color="#FFD700"
    ))

    # Manpower
    fig.add_trace(go.Scatter(
        x=df_view["date"],y=df_view["Total_Manpower"],
        name="Total Manpower",mode="lines+markers+text",
        text=[int(v) for v in df_view["Total_Manpower"]],
        textposition="top center",
        line=dict(color="#003A8C",width=3),
        marker=dict(size=9,color="#003A8C"),
        yaxis="y2",
    ))

    # NEW UPDATE — k-values near dates 🎯
    fig.add_trace(go.Scatter(
        x=df_view["date"],
        y=[0]*len(df_view),
        mode="text",
        text=[kfmt(v) for v in df_view["Total_WC_DT"]],
        textposition="bottom center",
        textfont=dict(size=12,color="#444"),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.update_layout(
        height=580,barmode="stack",
        hovermode="closest",
        xaxis=dict(tickangle=45,title="Date"),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower",overlaying="y",side="right")
    )

    st.plotly_chart(fig,use_container_width=True)

    # TABLE
    table = df_view.set_index("date")[[
        "Total_WC_DT","wc_mi","dt","Total_Manpower","ci","mi","in_house","supervisory"
    ]]
    table.index = table.index.strftime("%d-%b")
    table = table.T
    table.index = [
        "🔷 Total Meters (WC+DT)","WC-MI","DT",
        "🟢 Total Manpower","CI","MI","IN-HOUSE","Supervisory"
    ]

    def highlight_rows(row):
        if "Total" in row.name: return ["background-color:#CDE4FF;font-weight:bold"]*len(row)
        if "Manpower" in row.name: return ["background-color:#D4F7D4;font-weight:bold"]*len(row)
        return [""]*len(row)

    st.subheader("📋 Date-wise Summary Table")
    st.dataframe(table.style.apply(highlight_rows, axis=1),
                 use_container_width=True)

def show_dashboard():
    df = load_data()
    if df.empty:
        st.warning("Add data first from Admin Panel.")
        return

    st.markdown("### 🔍 Filters")
    min_d,max_d = df["date"].min(),df["date"].max()
    col1,col2,col3 = st.columns([2,1,1])
    with col1:
        view = st.radio("View Mode",["Combined","Package Wise"],horizontal=True)
    with col2:
        s = st.date_input("Start",min_d,min_value=min_d,max_value=max_d)
    with col3:
        e = st.date_input("End",max_d,min_value=min_d,max_value=max_d)
    if s > e:
        st.error("Start Date must be before End Date.")
        return

    df_range = df[(df["date"]>=s)&(df["date"]<=e)]
    if view=="Combined":
        grp=df_range.groupby("date").sum().reset_index()
        graph_and_table(grp)
    else:
        pkg=st.selectbox("Package",ALLOWED_PACKAGES)
        grp=df_range[df_range["package"]==pkg].groupby("date").sum().reset_index()
        graph_and_table(grp)

# ===================== ADMIN PANEL (unchanged) ===================== #
# ✔ No edits required — toolkit features intact

from admin_panel_code import show_admin   # your same admin panel code here

if mode=="Dashboard":
    show_dashboard()
else:
    show_admin()

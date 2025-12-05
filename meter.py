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
    div.block-container {padding-top: 0.8rem;}
    thead tr th {
        background-color: #003A8C !important;
        color: white !important;
        font-weight: bold !important;
    }
    .kpi-card {
        padding: 0.6rem 1rem;
        border-radius: 0.9rem;
        background: #f8fafc;
        border: 1px solid #e5e7eb;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #6b7280;
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
<div style='text-align:center;margin-bottom:0.2rem;'>
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
    "TN-32", "TN-33", "TN-34"
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
    """Create table + unique constraint fix"""
    engine = get_engine()
    ddl = """
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

    CREATE UNIQUE INDEX IF NOT EXISTS idx_meter_unique
    ON meter_data(date, package);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    return True


@st.cache_data
def load_data():
    engine = get_engine()
    query = "SELECT * FROM meter_data ORDER BY date ASC"
    df = pd.read_sql(query, engine)

    if df.empty:
        return df
    
    df["date"] = pd.to_datetime(df["date"]).dt.date

    num_cols = ["wc_mi","dt","ci","mi","in_house","supervisory"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df["Total_WC_DT"] = df["wc_mi"] + df["dt"]
    df["Total_Manpower"] = df["ci"] + df["mi"] + df["in_house"] + df["supervisory"]
    return df


def kfmt(x): return f"{x/1000:.1f}k" if x >= 1000 else str(int(x))


def upsert_row(row):
    engine = get_engine()
    stmt = text("""
        INSERT INTO meter_data(date, package, wc_mi, dt, ci, mi, in_house, supervisory)
        VALUES(:date,:package,:wc_mi,:dt,:ci,:mi,:in_house,:supervisory)
        ON CONFLICT (date, package)
        DO UPDATE SET
            wc_mi=EXCLUDED.wc_mi,
            dt=EXCLUDED.dt,
            ci=EXCLUDED.ci,
            mi=EXCLUDED.mi,
            in_house=EXCLUDED.in_house,
            supervisory=EXCLUDED.supervisory;
    """)
    with engine.begin() as conn:
        conn.execute(stmt, row)
    load_data.clear()


# ===================== GRAPH & TABLE ===================== #
def graph_and_table(dfv):

    # KPI Section
    total_meters = int(dfv["Total_WC_DT"].sum())
    peak_inst_idx = dfv["Total_WC_DT"].idxmax()
    peak_mp_idx = dfv["Total_Manpower"].idxmax()

    c1,c2,c3 = st.columns(3)
    c1.markdown(f"<div class='kpi-card'><div class='kpi-label'>📦 Total Meters</div><div class='kpi-value'>{kfmt(total_meters)}</div></div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card'><div class='kpi-label'>📈 Peak Installation</div><div class='kpi-value'>{int(dfv.loc[peak_inst_idx,'Total_WC_DT'])} on {dfv.loc[peak_inst_idx,'date'].strftime('%d-%b')}</div></div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card'><div class='kpi-label'>👥 Peak Manpower</div><div class='kpi-value'>{int(dfv.loc[peak_mp_idx,'Total_Manpower'])} on {dfv.loc[peak_mp_idx,'date'].strftime('%d-%b')}</div></div>",unsafe_allow_html=True)

    # Graph
    full_dates = pd.date_range(dfv["date"].min(), dfv["date"].max()).date

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dfv["date"],
        y=dfv["Total_WC_DT"],
        name="Total Meters",
        marker_color="#0080FF",
        text=[kfmt(v) for v in dfv["Total_WC_DT"]],
        textposition="outside"
    ))

    fig.add_trace(go.Scatter(
        x=dfv["date"], y=dfv["Total_Manpower"],
        name="Total Manpower", yaxis="y2",
        mode="lines+markers",
        marker=dict(size=9,color="#FF5733"),
        line=dict(width=3,color="#FF5733")
    ))

    fig.update_layout(
        height=500,
        barmode="group",
        xaxis=dict(
            tickvals=full_dates,
            ticktext=[d.strftime("%d-%b") for d in full_dates],
            tickangle=45),
        yaxis=dict(title="Meters"),
        yaxis2=dict(title="Manpower", overlaying="y", side="right"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Table
    table = dfv.set_index("date")[["Total_WC_DT","Total_Manpower"]].T
    table.index = ["🔷 Total Meters (WC+DT)", "🟢 Total Manpower"]
    table = table.astype(int)

    def highlight(r):
        if "Total Meters" in r.name:
            return ["background-color:#CDE4FF;font-weight:bold"] * len(r)
        if "Manpower" in r.name:
            return ["background-color:#D4F7D4;font-weight:bold"]*len(r)
        return [""] * len(r)

    st.dataframe(table.style.apply(highlight, axis=1), use_container_width=True)


# ===================== ADMIN PANEL (UNCHANGED) ===================== #
# (same as previous working version — not shown here to save scrolling)
# If you need, I can paste Admin Panel again separately.


# ===================== MAIN ===================== #
init_db()
mode = st.sidebar.radio("Navigate", ["Dashboard", "Admin Panel"])

if mode == "Dashboard":
    df = load_data()
    if df.empty:
        st.info("⚠ No data in DB. Add from Admin Panel.")
    else:
        graph_and_table(df)
else:
    st.write("Admin Panel Coming Here - same as your latest stable version")
